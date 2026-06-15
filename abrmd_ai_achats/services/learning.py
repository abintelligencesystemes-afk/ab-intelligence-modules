# -*- coding: utf-8 -*-
"""
Orchestrateur du pipeline OCR :
1. Lookup cache hash → si hit → retour direct (gratuit)
2. (futur) Pré-extraction texte rapide → lookup signature → contexte enrichi
3. Appel Worker OpenAI Vision
4. Stockage cache + maj scan record
"""
import json
import logging

from odoo import _
from odoo import fields as odoo_fields

from .ocr_client import call_worker, OcrWorkerError

_logger = logging.getLogger(__name__)


def run_pipeline(env, scan):
    """
    Lance le pipeline OCR complet sur un abrmd.ai.achat.scan.

    Mutates `scan` (write des champs source/state/extracted_data/cost_usd/...).
    Retourne le `scan` mis à jour.
    """
    if not scan.scanned_file:
        scan.write({"state": "failed", "error_message": _("Aucun fichier.")})
        return scan
    if not scan.file_hash:
        # Force recompute
        scan._compute_file_hash()

    # --- Étape 1 : cache hash -------------------------------------------------
    Cache = env["abrmd.ai.invoice.cache"]
    cached = Cache.lookup_by_hash(scan.file_hash)
    if cached:
        scan.write({
            "state": "cached",
            "source": "cache_hit",
            "extracted_data": cached.extracted_json,
            "cost_usd": 0.0,
            "cache_id": cached.id,
            "partner_id": cached.partner_id.id if cached.partner_id else False,
            "model_used": cached.model_used,
        })
        _apply_detected_fields(scan)
        _logger.info("[abrmd_ai_achats] Cache hit pour hash %s", scan.file_hash[:12])
        return scan

    # --- Étape 2 : signature fournisseur (contexte enrichi) -------------------
    Sig = env["abrmd.ai.supplier.signature"]
    threshold = float(env["ir.config_parameter"].sudo().get_param(
        "abrmd_ai_achats.signature_threshold", "0.8"))
    supplier_context = None
    # Pas encore de pré-extraction texte ici (V0.3) — on transmet juste le nom
    # des partners connus comme contexte général éventuel.
    # NOTE : pour V0.2 on n'extrait pas le texte avant Vision pour rester simple.
    #        L'enrichissement contexte se fera surtout après le 1er round de Vision.

    # --- Étape 3 : appel Worker OpenAI Vision --------------------------------
    try:
        result = call_worker(
            env=env,
            file_b64=scan.scanned_file.decode() if isinstance(scan.scanned_file, bytes) else scan.scanned_file,
            mime_type=scan.scanned_mime_type or "application/pdf",
            filename=scan.scanned_filename,
            supplier_context=supplier_context,
        )
    except OcrWorkerError as e:
        scan.write({
            "state": "failed",
            "error_message": str(e),
        })
        return scan

    data = result.get("data", {})
    meta = result.get("meta", {})

    scan.write({
        "state": "ocr_done",
        "source": "openai_vision",
        "extracted_data": json.dumps(data, ensure_ascii=False),
        "cost_usd": meta.get("cost_usd") or 0.0,
        "tokens_in": meta.get("tokens_in") or 0,
        "tokens_out": meta.get("tokens_out") or 0,
        "model_used": meta.get("model") or "",
        "duration_ms": meta.get("duration_ms") or 0,
    })
    _apply_detected_fields(scan)

    # --- Étape 4 : stockage cache pour future réutilisation gratuite ----------
    cache_rec = Cache.store(
        file_hash=scan.file_hash,
        extracted_json=json.dumps(data, ensure_ascii=False),
        filename=scan.scanned_filename,
        mime_type=scan.scanned_mime_type,
        file_size_kb=scan.file_size_kb,
        cost_usd=meta.get("cost_usd") or 0.0,
        tokens_in=meta.get("tokens_in") or 0,
        tokens_out=meta.get("tokens_out") or 0,
        model_used=meta.get("model"),
        mode=meta.get("mode"),
    )
    scan.write({"cache_id": cache_rec.id})

    return scan


def _apply_detected_fields(scan):
    """
    Parse le extracted_data JSON et remplit les champs détectés du scan
    (fournisseur, référence, date, montants, confidence).
    """
    if not scan.extracted_data:
        return
    try:
        data = json.loads(scan.extracted_data)
    except json.JSONDecodeError:
        return
    vals = {
        "fournisseur_detected": data.get("supplier_name"),
        "reference_detected": data.get("invoice_number"),
        "date_detected": data.get("invoice_date"),
        "montant_ht_detected": data.get("total_ht") or 0.0,
        "montant_ttc_detected": data.get("total_ttc") or 0.0,
        "tva_amount_detected": data.get("tva_amount") or 0.0,
        "confidence": data.get("confidence") or 0.0,
    }
    scan.write(vals)

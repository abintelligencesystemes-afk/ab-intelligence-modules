# -*- coding: utf-8 -*-
"""
Client HTTP vers le Worker Cloudflare abi-control-plane.

POST /api/ocr/invoice avec license_key + instance_uuid + image_b64 ou pdf_b64.
Retour : { ok, data, meta } ou { ok: false, error, reason }.

Utilise urllib.request (stdlib) — pas de dépendance externe (compat Odoo SaaS).
"""
import json
import logging
import urllib.request
import urllib.error
import base64

_logger = logging.getLogger(__name__)


class OcrWorkerError(Exception):
    """Erreur lors de l'appel au Worker OCR."""
    pass


def call_worker(env, file_b64, mime_type, filename=None, supplier_context=None):
    """
    Appelle le Worker OCR avec un fichier base64.

    Args:
        env: Odoo env (pour ir.config_parameter)
        file_b64: contenu base64 du fichier (sans préfixe data:)
        mime_type: 'application/pdf' | 'image/png' | 'image/jpeg'
        filename: nom original du fichier (pour Files API si PDF)
        supplier_context: contexte fournisseur connu (signature match)

    Returns:
        dict { ok, data, meta } ou raise OcrWorkerError.
    """
    ICP = env["ir.config_parameter"].sudo()

    # Kill switch
    if ICP.get_param("abrmd_ai_achats.killed", "False") == "True":
        raise OcrWorkerError("Module désactivé (kill switch actif).")

    worker_url = ICP.get_param("abrmd_ai_achats.worker_url")
    license_key = ICP.get_param("abrmd_ai_achats.license_key")
    instance_uuid = ICP.get_param("abrmd_ai_achats.instance_uuid")
    model = ICP.get_param("abrmd_ai_achats.openai_model", "gpt-4o")
    timeout = int(ICP.get_param("abrmd_ai_achats.http_timeout_sec", "60"))

    if not worker_url:
        raise OcrWorkerError("abrmd_ai_achats.worker_url non configuré.")
    if not license_key:
        raise OcrWorkerError("abrmd_ai_achats.license_key non configuré.")
    if not instance_uuid:
        raise OcrWorkerError("abrmd_ai_achats.instance_uuid non configuré.")

    payload = {
        "license_key": license_key,
        "instance_uuid": instance_uuid,
        "filename": filename or "invoice",
        "model": model,
    }
    if supplier_context:
        payload["supplier_context"] = supplier_context

    if mime_type == "application/pdf":
        payload["pdf_b64"] = file_b64
    elif mime_type in ("image/png", "image/jpeg"):
        payload["image_b64"] = file_b64
        payload["image_mime_type"] = mime_type
    else:
        raise OcrWorkerError(f"Type MIME non supporté : {mime_type}")

    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        worker_url,
        data=data_bytes,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "abrmd-ai-achats/0.2.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            result = json.loads(body)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        _logger.error("[abrmd_ai_achats] Worker HTTP %s : %s", e.code, body[:500])
        raise OcrWorkerError(f"Worker HTTP {e.code} : {body[:300]}")
    except urllib.error.URLError as e:
        _logger.error("[abrmd_ai_achats] Worker URLError : %s", e)
        raise OcrWorkerError(f"Worker injoignable : {e.reason}")
    except json.JSONDecodeError as e:
        _logger.error("[abrmd_ai_achats] Worker JSON invalide : %s", e)
        raise OcrWorkerError(f"Réponse Worker non-JSON : {e}")

    if not result.get("ok"):
        raise OcrWorkerError(f"Worker error : {result.get('error')} ({result.get('reason')})")

    return result

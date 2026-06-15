# -*- coding: utf-8 -*-
"""
Extension account.move :
- Bouton « OCR via OpenAI » (lance le pipeline depuis une facture brouillon)
- Bouton « Corriger & Apprendre » (enregistre les corrections d'Anthony dans les référentiels)
- Champs de traçabilité (scan_id, source, coût)
"""
import json
import base64
import hashlib

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    abrmd_ai_scan_id = fields.Many2one(
        "abrmd.ai.achat.scan",
        string="Scan OCR AI Achats",
        ondelete="set null",
        copy=False,
        help="Trace du dernier scan OCR appliqué à cette facture.",
    )
    abrmd_ai_source = fields.Selection(
        related="abrmd_ai_scan_id.source",
        string="Source OCR",
        readonly=True,
    )
    abrmd_ai_cost_usd = fields.Float(
        related="abrmd_ai_scan_id.cost_usd",
        string="Coût OCR (USD)",
        readonly=True,
    )

    # --- Actions ------------------------------------------------------------

    def action_abrmd_ai_ocr_from_attachment(self):
        """
        Lance l'OCR sur le premier attachment PDF/image lié à cette facture.
        Crée un abrmd.ai.achat.scan, l'exécute, puis pré-remplit les lignes.
        """
        self.ensure_one()
        if self.move_type not in ("in_invoice", "in_refund"):
            raise UserError(_("OCR disponible uniquement pour les factures fournisseurs."))

        # Cherche un attachment compatible (PDF / image) lié à ce move
        att = self.env["ir.attachment"].search([
            ("res_model", "=", "account.move"),
            ("res_id", "=", self.id),
            ("mimetype", "in", ["application/pdf", "image/png", "image/jpeg"]),
        ], limit=1, order="id desc")
        if not att:
            raise UserError(_(
                "Aucun PDF/image lié à cette facture. "
                "Glisse un fichier dans les pièces jointes puis relance."
            ))

        scan = self.env["abrmd.ai.achat.scan"].create({
            "scanned_file": att.datas,
            "scanned_filename": att.name,
            "scanned_mime_type": att.mimetype,
            "scan_type": "invoice",
            "state": "ocr_pending",
        })
        scan = self.env["abrmd.ai.achat.scan"]._run_ocr_pipeline(scan)

        # Lie le scan + applique les valeurs détectées (sans écraser si déjà rempli)
        self.abrmd_ai_scan_id = scan.id
        scan.move_id = self.id
        self._apply_ocr_extraction(scan)

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("OCR terminé"),
                "message": _("Source : %s — coût : %.4f USD") % (
                    dict(scan._fields["source"].selection).get(scan.source, scan.source),
                    scan.cost_usd or 0.0,
                ),
                "type": "success",
                "sticky": False,
            },
        }

    def _apply_ocr_extraction(self, scan):
        """Applique les données extraites au move + crée les lignes."""
        self.ensure_one()
        if not scan.extracted_data:
            return

        try:
            data = json.loads(scan.extracted_data)
        except json.JSONDecodeError:
            return

        # Match fournisseur (signature ou matching simple)
        partner = scan.partner_id
        if not partner and data.get("supplier_name"):
            partner = self._abrmd_ai_match_partner(
                name=data.get("supplier_name"),
                vat=data.get("supplier_vat"),
            )
        vals = {}
        if partner and not self.partner_id:
            vals["partner_id"] = partner.id
        if data.get("invoice_date") and not self.invoice_date:
            vals["invoice_date"] = data["invoice_date"]
        if data.get("invoice_number") and not self.ref:
            vals["ref"] = data["invoice_number"]
        if vals:
            self.write(vals)

        # Lignes (uniquement si pas déjà présentes pour ne pas écraser)
        if not self.invoice_line_ids and data.get("lines"):
            line_vals = []
            for line in data["lines"]:
                line_vals.append((0, 0, self._abrmd_ai_build_line_vals(line, partner)))
            if line_vals:
                self.write({"invoice_line_ids": line_vals})

    def _abrmd_ai_match_partner(self, name=None, vat=None):
        """Match res.partner via signature ou recherche standard."""
        Sig = self.env["abrmd.ai.supplier.signature"]
        Partner = self.env["res.partner"]
        # 1. VAT exact
        if vat:
            p = Partner.search([("vat", "=", vat)], limit=1)
            if p:
                return p
        # 2. signature partner pré-existant
        if name:
            p = Partner.search([
                ("name", "=ilike", name),
                ("supplier_rank", ">", 0),
            ], limit=1)
            if p:
                return p
            p = Partner.search([
                ("name", "ilike", name),
                ("supplier_rank", ">", 0),
            ], limit=1)
            if p:
                return p
        return False

    def _abrmd_ai_build_line_vals(self, line, partner):
        """Construit les vals d'une ligne facture, en utilisant le référentiel produit."""
        Match = self.env["abrmd.ai.product.match"]
        threshold = float(self.env["ir.config_parameter"].sudo().get_param(
            "abrmd_ai_achats.product_match_threshold", "0.8"))
        product = False
        if partner:
            product, _rec, _score = Match.match_line(
                partner_id=partner.id,
                supplier_ref=line.get("supplier_ref"),
                supplier_name=line.get("description"),
                threshold=threshold,
            )
        vals = {
            "name": line.get("description") or "",
            "quantity": line.get("quantity") or 1.0,
            "price_unit": line.get("unit_price") or 0.0,
        }
        if product:
            vals["product_id"] = product.id
        return vals

    def action_abrmd_ai_correct_and_learn(self):
        """
        « Corriger & Apprendre » : Anthony a corrigé manuellement la facture
        (partner_id, lignes, product_id). On enregistre ces corrections dans
        les référentiels pour les prochaines factures.
        """
        self.ensure_one()
        if not self.abrmd_ai_scan_id:
            raise UserError(_(
                "Cette facture n'a pas de scan OCR associé. "
                "Lance d'abord 'OCR via OpenAI' depuis l'attachment."
            ))
        scan = self.abrmd_ai_scan_id
        Sig = self.env["abrmd.ai.supplier.signature"]
        Match = self.env["abrmd.ai.product.match"]

        learned = {"partner": False, "lines": 0}

        # Apprentissage signature fournisseur
        if self.partner_id and scan.raw_text:
            Sig.learn_or_update(
                partner_id=self.partner_id.id,
                raw_text=scan.raw_text,
                vat=self.partner_id.vat,
                siret=self.partner_id.siret if "siret" in self.partner_id._fields else None,
            )
            learned["partner"] = True
            scan.partner_id = self.partner_id.id

        # Apprentissage produits ligne par ligne
        try:
            data = json.loads(scan.extracted_data) if scan.extracted_data else {}
        except json.JSONDecodeError:
            data = {}
        ocr_lines = data.get("lines", [])

        for idx, line in enumerate(self.invoice_line_ids):
            if not line.product_id:
                continue
            ocr_line = ocr_lines[idx] if idx < len(ocr_lines) else {}
            Match.learn(
                partner_id=self.partner_id.id if self.partner_id else None,
                product_id=line.product_id.id,
                supplier_ref=ocr_line.get("supplier_ref"),
                supplier_name=ocr_line.get("description") or line.name,
                unit_price=line.price_unit,
            )
            learned["lines"] += 1

        scan.write({"validated": True, "state": "validated"})

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Corrections enregistrées"),
                "message": _("Signature fournisseur : %s — Produits appris : %d") % (
                    _("oui") if learned["partner"] else _("non"),
                    learned["lines"],
                ),
                "type": "success",
                "sticky": False,
            },
        }

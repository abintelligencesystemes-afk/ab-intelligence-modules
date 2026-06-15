# -*- coding: utf-8 -*-
"""
Wizard standalone : Anthony peut scanner un PDF/image sans avoir d'account.move
préexistant. Crée un abrmd.ai.achat.scan + pré-rempli une draft account.move
si confiance suffisante.
"""
from odoo import models, fields, _


class AbrmdAiScanWizard(models.TransientModel):
    _name = "abrmd.ai.scan.wizard"
    _description = "Wizard scan OCR autonome"

    scanned_file = fields.Binary(string="Fichier à scanner", required=True)
    scanned_filename = fields.Char(string="Nom fichier")
    mime_type = fields.Selection(
        [
            ("application/pdf", "PDF"),
            ("image/png", "PNG"),
            ("image/jpeg", "JPEG"),
        ],
        default="application/pdf",
        required=True,
    )
    auto_create_move = fields.Boolean(
        string="Créer brouillon facture automatiquement",
        default=True,
    )

    def action_scan(self):
        self.ensure_one()
        Scan = self.env["abrmd.ai.achat.scan"]
        scan = Scan.create({
            "scanned_file": self.scanned_file,
            "scanned_filename": self.scanned_filename or "document",
            "scanned_mime_type": self.mime_type,
            "scan_type": "invoice",
            "state": "ocr_pending",
        })
        Scan._run_ocr_pipeline(scan)

        # Auto-create move si demandé
        move = False
        if self.auto_create_move and scan.state in ("ocr_done", "cached"):
            move_vals = {"move_type": "in_invoice"}
            if scan.partner_id:
                move_vals["partner_id"] = scan.partner_id.id
            move = self.env["account.move"].create(move_vals)
            move.abrmd_ai_scan_id = scan.id
            scan.move_id = move.id
            move._apply_ocr_extraction(scan)

        # Retourne la vue du scan ou du move
        if move:
            return {
                "type": "ir.actions.act_window",
                "res_model": "account.move",
                "res_id": move.id,
                "view_mode": "form",
                "target": "current",
            }
        return {
            "type": "ir.actions.act_window",
            "res_model": "abrmd.ai.achat.scan",
            "res_id": scan.id,
            "view_mode": "form",
            "target": "current",
        }

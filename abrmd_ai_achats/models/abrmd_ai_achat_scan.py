# -*- coding: utf-8 -*-
"""
Modèle principal du scan OCR (historique + audit trail).

Chaque scan = 1 PDF/image envoyé à OpenAI Vision ou résolu par cache/signature.
"""
import json
import hashlib

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AbrmdAiAchatScan(models.Model):
    _name = "abrmd.ai.achat.scan"
    _description = "Scan OCR facture fournisseur (AB Intelligence)"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char(
        string="Référence",
        required=True,
        readonly=True,
        default=lambda self: _("Nouveau"),
        copy=False,
    )
    scan_type = fields.Selection(
        [
            ("invoice", "Facture fournisseur"),
            ("purchase_order", "Commande / Devis fournisseur"),
            ("reception_br", "Bon de réception"),
        ],
        default="invoice",
        required=True,
    )
    state = fields.Selection(
        [
            ("draft", "Brouillon"),
            ("cached", "Résolu par cache (0 €)"),
            ("ocr_pending", "OCR en cours"),
            ("ocr_done", "OCR terminé"),
            ("review", "À valider"),
            ("validated", "Validé"),
            ("failed", "Échec"),
        ],
        default="draft",
        tracking=True,
    )

    # Input
    scanned_file = fields.Binary(
        string="Fichier scanné",
        attachment=True,
        required=True,
    )
    scanned_filename = fields.Char(string="Nom du fichier")
    scanned_mime_type = fields.Char(string="Type MIME")
    file_hash = fields.Char(
        string="Hash SHA256",
        compute="_compute_file_hash",
        store=True,
        index=True,
    )
    file_size_kb = fields.Float(string="Taille (Ko)", compute="_compute_file_hash", store=True)

    # Output OCR
    raw_text = fields.Text(string="Texte OCR brut")
    extracted_data = fields.Text(string="JSON extrait OpenAI")

    # Données détectées
    fournisseur_detected = fields.Char(string="Fournisseur détecté")
    reference_detected = fields.Char(string="Référence facture détectée")
    date_detected = fields.Date(string="Date facture détectée")
    montant_ht_detected = fields.Float(string="Montant HT détecté")
    montant_ttc_detected = fields.Float(string="Montant TTC détecté")
    tva_amount_detected = fields.Float(string="Montant TVA détecté")
    confidence = fields.Float(string="Confiance", digits=(3, 2))

    # Méta coût / source
    source = fields.Selection(
        [
            ("openai_vision", "OpenAI Vision (payant)"),
            ("cache_hit", "Cache (gratuit)"),
            ("signature_match", "Signature fournisseur reconnue"),
            ("manual", "Saisie manuelle"),
        ],
        default="openai_vision",
    )
    cost_usd = fields.Float(string="Coût USD", digits=(8, 6))
    tokens_in = fields.Integer(string="Tokens entrée")
    tokens_out = fields.Integer(string="Tokens sortie")
    model_used = fields.Char(string="Modèle OpenAI")
    duration_ms = fields.Integer(string="Durée (ms)")

    # Relations
    partner_id = fields.Many2one(
        "res.partner",
        string="Fournisseur résolu",
        domain="[('supplier_rank', '>', 0)]",
        tracking=True,
    )
    move_id = fields.Many2one(
        "account.move",
        string="Facture créée",
        ondelete="set null",
    )
    purchase_order_id = fields.Many2one(
        "purchase.order",
        string="Commande liée",
        ondelete="set null",
    )
    stock_picking_id = fields.Many2one(
        "stock.picking",
        string="Réception liée",
        ondelete="set null",
    )
    cache_id = fields.Many2one(
        "abrmd.ai.invoice.cache",
        string="Cache utilisé",
        ondelete="set null",
    )

    validated = fields.Boolean(string="Validé Anthony", tracking=True)
    error_message = fields.Text(string="Erreur")

    # --- Lifecycle -----------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("Nouveau")) == _("Nouveau"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "abrmd.ai.achat.scan"
                ) or "AIACHAT/0001"
        return super().create(vals_list)

    @api.depends("scanned_file")
    def _compute_file_hash(self):
        import base64 as _b64
        for rec in self:
            if not rec.scanned_file:
                rec.file_hash = False
                rec.file_size_kb = 0.0
                continue
            try:
                raw = _b64.b64decode(rec.scanned_file)
                rec.file_hash = hashlib.sha256(raw).hexdigest()
                rec.file_size_kb = len(raw) / 1024.0
            except Exception:
                rec.file_hash = False
                rec.file_size_kb = 0.0

    # --- Actions UI ----------------------------------------------------------

    def action_run_ocr(self):
        """Lance la chaîne OCR : cache → signature → OpenAI Vision."""
        self.ensure_one()
        if not self.scanned_file:
            raise UserError(_("Aucun fichier à scanner."))
        # Délégué au service learning (orchestrateur)
        result = self.env["abrmd.ai.achat.scan"]._run_ocr_pipeline(self)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("OCR terminé"),
                "message": _("Source : %s — coût : %.4f USD") % (
                    dict(self._fields["source"].selection).get(result.source, result.source),
                    result.cost_usd or 0.0,
                ),
                "type": "success",
                "sticky": False,
            },
        }

    @api.model
    def _run_ocr_pipeline(self, scan):
        """
        Orchestre la chaîne d'extraction :
        1. cache hash
        2. (futur) signature fournisseur → contexte enrichi
        3. appel Worker OpenAI Vision
        4. enregistre résultat + crée cache
        """
        from ..services.learning import run_pipeline
        return run_pipeline(self.env, scan)

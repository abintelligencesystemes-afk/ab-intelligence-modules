# -*- coding: utf-8 -*-
"""
Cache des factures déjà OCRisées (par hash SHA256 du PDF/image).

Quand Anthony re-scanne une facture déjà traitée (rare mais utile en dev/test),
on retourne le résultat précédent au lieu de re-payer OpenAI Vision.

Coût : 0 € si hit cache.
"""
from odoo import models, fields, api


class AbrmdAiInvoiceCache(models.Model):
    _name = "abrmd.ai.invoice.cache"
    _description = "Cache des extractions OCR factures (hash SHA256 → JSON)"
    _order = "create_date desc"
    _rec_name = "file_hash"

    file_hash = fields.Char(
        string="Hash SHA256",
        required=True,
        index=True,
        help="SHA256 hex du fichier brut (PDF/image).",
    )
    filename = fields.Char(string="Nom fichier d'origine")
    mime_type = fields.Char(string="Type MIME")
    file_size_kb = fields.Float(string="Taille (Ko)")

    # Résultat OCR (JSON sérialisé)
    extracted_json = fields.Text(
        string="JSON extrait OpenAI",
        required=True,
        help="Payload JSON brut renvoyé par le Worker / OpenAI Vision.",
    )

    # Méta usage
    partner_id = fields.Many2one(
        "res.partner",
        string="Fournisseur résolu",
        ondelete="set null",
        help="Partner final après confirmation Anthony (pour stats).",
    )
    move_id = fields.Many2one(
        "account.move",
        string="Facture créée",
        ondelete="set null",
    )

    # Stats coût (pour dashboard économies)
    cost_usd = fields.Float(string="Coût USD", digits=(8, 6))
    tokens_in = fields.Integer(string="Tokens entrée")
    tokens_out = fields.Integer(string="Tokens sortie")
    model_used = fields.Char(string="Modèle OpenAI", default="gpt-4o")
    mode = fields.Selection(
        [("image", "Image"), ("pdf_file", "PDF Files API")],
        string="Mode appel",
    )

    # Compteur réutilisation cache (combien de fois on a évité un appel OpenAI grâce à ce hash)
    hit_count = fields.Integer(
        string="Hits cache",
        default=0,
        help="Nombre de fois où ce hash a été retrouvé sans repayer OpenAI.",
    )
    last_hit_date = fields.Datetime(string="Dernier hit")

    _sql_constraints = [
        (
            "file_hash_unique",
            "UNIQUE(file_hash)",
            "Un seul cache par hash SHA256 (déduplication automatique).",
        ),
    ]

    @api.model
    def lookup_by_hash(self, file_hash):
        """Retourne le cache existant pour ce hash, ou None."""
        rec = self.search([("file_hash", "=", file_hash)], limit=1)
        if rec:
            rec.write({
                "hit_count": rec.hit_count + 1,
                "last_hit_date": fields.Datetime.now(),
            })
        return rec or None

    @api.model
    def store(self, file_hash, extracted_json, **kwargs):
        """Crée ou met à jour un cache pour ce hash."""
        existing = self.search([("file_hash", "=", file_hash)], limit=1)
        vals = {
            "file_hash": file_hash,
            "extracted_json": extracted_json,
            **{k: v for k, v in kwargs.items() if v is not None},
        }
        if existing:
            existing.write(vals)
            return existing
        return self.create(vals)

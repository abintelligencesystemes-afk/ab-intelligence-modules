# -*- coding: utf-8 -*-
"""Modèle abrmd.grow.veille.video — top vidéos analysées.

Alimenté par un cron (V0.3 — branchement YouTube Data API / TikTok stub).
Permet d'extraire des patterns réutilisables.

RGPD : aucun PII direct. Le ``creator_handle`` peut être hashé via
``hashlib`` côté cron si Anthony ne veut pas stocker le pseudo clair.
"""
import hashlib
import json

from odoo import _, api, fields, models


PLATFORM_SELECTION = [
    ("tiktok", "TikTok"),
    ("instagram", "Instagram"),
    ("youtube", "YouTube"),
    ("linkedin", "LinkedIn"),
    ("twitter", "X / Twitter"),
]


class AbrmdGrowVeilleVideo(models.Model):
    _name = "abrmd.grow.veille.video"
    _description = "Top vidéo veille (analyse pattern)"
    _order = "composite_score desc, published_at desc"
    _rec_name = "title"

    platform = fields.Selection(
        selection=PLATFORM_SELECTION,
        string="Plateforme",
        required=True,
        default="youtube",
    )
    external_id = fields.Char(
        string="ID externe (plateforme)",
        required=True,
        help="ID natif de la vidéo (ex. YouTube videoId, TikTok aweme_id).",
    )
    title = fields.Char(string="Titre", required=True)
    url = fields.Char(string="URL publique")
    transcript = fields.Text(string="Transcript / sous-titres (extrait)")
    hook_first_3s = fields.Char(
        string="Hook (3 premières secondes)",
        help="Extrait par l'IA d'analyse des patterns.",
    )
    cta = fields.Char(string="CTA détecté")
    engagement_rate = fields.Float(string="Taux engagement (likes+commentaires/vues)")
    save_rate = fields.Float(string="Taux sauvegarde / partage")
    views = fields.Integer(string="Vues")
    likes = fields.Integer(string="Likes")
    comments = fields.Integer(string="Commentaires")
    published_at = fields.Datetime(string="Date publication")
    creator_handle = fields.Char(
        string="Créateur (pseudo)",
        help="Stocké en clair par défaut. Peut être hashé via "
             "``rec.action_hash_creator()`` pour anonymisation RGPD.",
    )
    creator_hash = fields.Char(
        string="Hash créateur (SHA256)",
        readonly=True,
        help="Calculé via action_hash_creator() — pour anonymisation.",
    )
    pattern_tags = fields.Char(
        string="Tags pattern (JSON)",
        help='JSON simple type ["hook_curiosity", "cta_dm", "pov_format"].',
    )
    pattern_id = fields.Many2one(
        comodel_name="abrmd.grow.pattern",
        string="Pattern principal lié",
        ondelete="set null",
    )
    composite_score = fields.Float(
        string="Score composite",
        default=0.0,
        help="Composite engagement × récence × portée.",
    )
    raw_data = fields.Text(
        string="Données brutes (JSON)",
        help="Payload brut de l'API source (audit / replay).",
    )
    active = fields.Boolean(string="Actif", default=True)

    _sql_constraints = [
        (
            "abrmd_grow_veille_unique",
            "unique(platform, external_id)",
            "Cette vidéo existe déjà pour cette plateforme.",
        ),
    ]

    @api.model
    def upsert_video(self, platform, external_id, **vals):
        """Helper : upsert d'une vidéo veille (utilisé par les crons)."""
        existing = self.search([
            ("platform", "=", platform),
            ("external_id", "=", external_id),
        ], limit=1)
        payload = {"platform": platform, "external_id": external_id}
        payload.update({k: v for k, v in vals.items() if v is not None})
        if existing:
            existing.write(payload)
            return existing
        return self.create(payload)

    def action_hash_creator(self):
        """Hash SHA256 du creator_handle pour anonymisation RGPD."""
        for rec in self:
            if rec.creator_handle:
                h = hashlib.sha256(rec.creator_handle.encode("utf-8")).hexdigest()
                rec.creator_hash = h[:32]  # 32 chars suffisent

    def action_parse_pattern_tags(self):
        """Parse pattern_tags JSON et tente d'associer à un pattern existant."""
        Pattern = self.env["abrmd.grow.pattern"]
        for rec in self:
            if not rec.pattern_tags:
                continue
            try:
                tags = json.loads(rec.pattern_tags)
            except Exception:
                continue
            if not isinstance(tags, list):
                continue
            for tag in tags:
                pattern = Pattern.search([("name", "=", tag)], limit=1)
                if pattern:
                    rec.pattern_id = pattern.id
                    break

    def action_view_pattern(self):
        self.ensure_one()
        if not self.pattern_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "res_model": "abrmd.grow.pattern",
            "res_id": self.pattern_id.id,
            "view_mode": "form",
            "target": "current",
        }

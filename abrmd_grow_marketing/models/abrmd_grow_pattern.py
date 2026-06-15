# -*- coding: utf-8 -*-
"""Modèle abrmd.grow.pattern — pattern réutilisable (hook, CTA, structure).

Alimenté manuellement par Anthony et par la veille top vidéos
(abrmd.grow.veille.video). Score composite = engagement_rate × recency.
"""
from datetime import datetime, timedelta

from odoo import api, fields, models


PLATFORM_SELECTION = [
    ("tiktok", "TikTok"),
    ("instagram", "Instagram"),
    ("youtube", "YouTube"),
    ("linkedin", "LinkedIn"),
    ("facebook", "Facebook"),
    ("twitter", "X / Twitter"),
    ("threads", "Threads"),
    ("multi", "Multi-plateforme"),
]

PATTERN_TYPE_SELECTION = [
    ("hook", "Hook (accroche 3 premières sec.)"),
    ("cta", "CTA (call-to-action)"),
    ("structure", "Structure narrative"),
    ("format", "Format visuel"),
    ("trend", "Trend / Tendance"),
]


class AbrmdGrowPattern(models.Model):
    _name = "abrmd.grow.pattern"
    _description = "Pattern marketing réutilisable"
    _order = "composite_score desc, last_seen desc"

    name = fields.Char(string="Nom du pattern", required=True)
    description = fields.Text(string="Description / mode d'emploi")
    examples = fields.Text(
        string="Exemples concrets",
        help="Quelques exemples bruts pris dans la veille (titres, accroches).",
    )
    platform = fields.Selection(
        selection=PLATFORM_SELECTION,
        string="Plateforme dominante",
        default="multi",
        required=True,
    )
    pattern_type = fields.Selection(
        selection=PATTERN_TYPE_SELECTION,
        string="Type de pattern",
        required=True,
        default="hook",
    )
    composite_score = fields.Float(
        string="Score composite",
        default=0.0,
        help="Engagement × récence — recalculé par cron à partir de la veille.",
    )
    recency_weight = fields.Float(
        string="Poids récence",
        compute="_compute_recency_weight",
        store=True,
    )
    last_seen = fields.Date(string="Vu pour la dernière fois")
    active = fields.Boolean(string="Actif", default=True)
    notes = fields.Text(string="Notes Anthony")

    # Relations
    veille_video_ids = fields.One2many(
        comodel_name="abrmd.grow.veille.video",
        inverse_name="pattern_id",
        string="Vidéos veille associées",
    )
    veille_count = fields.Integer(
        string="Nb vidéos veille",
        compute="_compute_veille_count",
    )
    idea_ids = fields.One2many(
        comodel_name="abrmd.grow.idea",
        inverse_name="pattern_id",
        string="Idées générées",
    )

    _sql_constraints = [
        ("abrmd_grow_pattern_name_uniq", "unique(name)", "Ce pattern existe déjà."),
    ]

    @api.depends("last_seen")
    def _compute_recency_weight(self):
        """Pondération exponentielle décroissante sur 30j."""
        today = fields.Date.context_today(self)
        for rec in self:
            if not rec.last_seen:
                rec.recency_weight = 0.1
                continue
            delta = (today - rec.last_seen).days
            if delta < 0:
                delta = 0
            # weight = 1 si vu aujourd'hui, ~0.5 à J+7, ~0.1 à J+30
            rec.recency_weight = max(0.05, 1.0 / (1.0 + delta / 7.0))

    @api.depends("veille_video_ids")
    def _compute_veille_count(self):
        for rec in self:
            rec.veille_count = len(rec.veille_video_ids)

    def action_view_veille_videos(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Vidéos veille — %s" % self.name,
            "res_model": "abrmd.grow.veille.video",
            "view_mode": "list,form,kanban",
            "domain": [("pattern_id", "=", self.id)],
            "context": {"default_pattern_id": self.id},
        }

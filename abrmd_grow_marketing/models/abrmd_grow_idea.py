# -*- coding: utf-8 -*-
"""Modèle abrmd.grow.idea — file d'idées de posts.

Une idée peut venir :
- d'Anthony (source=manual)
- du cron quotidien qui propose 3 idées chaque matin (source=cron_daily)
- de la veille patterns (source=cron_pattern)
- d'un LLM (source=llm)

Workflow : proposed → approved → used (ou rejected).
"""
import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


CANAL_SUGGESTED = [
    ("linkedin", "LinkedIn"),
    ("instagram", "Instagram"),
    ("facebook", "Facebook"),
    ("twitter", "X / Twitter"),
    ("youtube", "YouTube"),
    ("threads", "Threads"),
    ("tiktok", "TikTok"),
]


class AbrmdGrowIdea(models.Model):
    _name = "abrmd.grow.idea"
    _description = "Idée de post Grow Marketing"
    _order = "priority desc, create_date desc, id desc"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(string="Idée (titre court)", required=True, tracking=True)
    description = fields.Text(string="Description / brief", tracking=True)
    canal_suggested = fields.Selection(
        selection=CANAL_SUGGESTED,
        string="Canal suggéré",
        default="linkedin",
        tracking=True,
    )
    source = fields.Selection(
        selection=[
            ("manual", "Manuel (Anthony)"),
            ("cron_daily", "Cron quotidien"),
            ("cron_pattern", "Veille patterns"),
            ("llm", "Génération LLM"),
        ],
        string="Source",
        default="manual",
        required=True,
        tracking=True,
    )
    state = fields.Selection(
        selection=[
            ("proposed", "Proposée"),
            ("approved", "Approuvée"),
            ("rejected", "Rejetée"),
            ("used", "Utilisée"),
        ],
        string="État",
        default="proposed",
        tracking=True,
        required=True,
    )
    priority = fields.Selection(
        selection=[
            ("0", "Basse"),
            ("1", "Moyenne"),
            ("2", "Haute"),
        ],
        string="Priorité",
        default="1",
        tracking=True,
    )
    pattern_id = fields.Many2one(
        comodel_name="abrmd.grow.pattern",
        string="Pattern d'origine",
        ondelete="set null",
    )
    product_id = fields.Many2one(
        comodel_name="product.template",
        string="Produit lié",
        ondelete="set null",
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Partenaire lié",
        ondelete="set null",
    )
    tag_ids = fields.Many2many(
        comodel_name="abrmd.grow.tag",
        relation="abrmd_grow_idea_tag_rel",
        column1="idea_id",
        column2="tag_id",
        string="Tags",
    )
    created_by_cron = fields.Boolean(
        string="Créée par cron",
        default=False,
        readonly=True,
    )
    color = fields.Integer(string="Couleur Kanban")

    # Relation inverse vers les posts qui ont utilisé cette idée
    post_ids = fields.One2many(
        comodel_name="abrmd.grow.post",
        inverse_name="idea_id",
        string="Posts générés",
    )
    post_count = fields.Integer(
        string="Nb posts",
        compute="_compute_post_count",
    )

    @api.depends("post_ids")
    def _compute_post_count(self):
        for rec in self:
            rec.post_count = len(rec.post_ids)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_approve(self):
        for rec in self:
            rec.state = "approved"
        return True

    def action_reject(self):
        for rec in self:
            rec.state = "rejected"
        return True

    def action_mark_used(self):
        for rec in self:
            rec.state = "used"
        return True

    def action_back_to_proposed(self):
        for rec in self:
            rec.state = "proposed"
        return True

    def action_create_post_draft(self):
        """Ouvre le wizard de génération de post avec l'idée pré-remplie."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Générer post depuis l'idée"),
            "res_model": "abrmd.grow.generate.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_idea_id": self.id,
                "default_canal": self.canal_suggested or "linkedin",
                "default_product_id": self.product_id.id if self.product_id else False,
                "default_angle": self.description and self.description[:200] or False,
            },
        }

    def action_view_posts(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Posts générés à partir de cette idée"),
            "res_model": "abrmd.grow.post",
            "view_mode": "kanban,list,form,calendar",
            "domain": [("idea_id", "=", self.id)],
            "context": {"default_idea_id": self.id},
        }


class AbrmdGrowTag(models.Model):
    """Tags simples partagés entre idées et médias."""
    _name = "abrmd.grow.tag"
    _description = "Tag Grow Marketing"
    _order = "name"

    name = fields.Char(string="Nom", required=True)
    color = fields.Integer(string="Couleur")

    _sql_constraints = [
        ("abrmd_grow_tag_name_uniq", "unique(name)", "Ce tag existe déjà."),
    ]

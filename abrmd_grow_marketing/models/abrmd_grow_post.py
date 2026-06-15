# -*- coding: utf-8 -*-
"""Modèle abrmd.grow.post — post éditorial multi-canal piloté par IA.

V0.2 :
- Champs métier étendus : idea, patterns, médias, published_date, ai_model,
  partner_id, char_limit_canal, over_limit.
- Bouton Régénérer brouillon (relance wizard avec mêmes paramètres).
- Bouton Marquer publié inscrit published_date automatiquement.
- RGPD : aucune FK obligatoire vers res.users / res.partner.
"""
import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)

CANAL_SELECTION = [
    ("linkedin", "LinkedIn"),
    ("instagram", "Instagram"),
    ("facebook", "Facebook"),
    ("twitter", "X / Twitter"),
    ("youtube", "YouTube"),
    ("threads", "Threads"),
    ("tiktok", "TikTok"),
]

# Limites souples — au-delà on flag over_limit=True (pas de blocage dur).
CHAR_LIMITS = {
    "linkedin": 3000,
    "instagram": 2200,
    "facebook": 5000,
    "twitter": 280,
    "youtube": 5000,
    "threads": 500,
    "tiktok": 2200,
}


class AbrmdGrowPost(models.Model):
    _name = "abrmd.grow.post"
    _description = "Post éditorial Grow Marketing (Anthony Growth Agent)"
    _order = "scheduled_date desc, id desc"
    _rec_name = "title"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    title = fields.Char(string="Titre", required=True, tracking=True)
    content = fields.Text(string="Contenu (texte du post)", tracking=True)
    canal = fields.Selection(
        selection=CANAL_SELECTION,
        string="Canal",
        required=True,
        default="linkedin",
        tracking=True,
    )
    scheduled_date = fields.Date(
        string="Date de publication prévue",
        tracking=True,
        index=True,
    )
    published_date = fields.Datetime(
        string="Date de publication effective",
        readonly=True,
        tracking=True,
    )
    published_url = fields.Char(
        string="URL post publié",
        help="URL du post une fois publié sur le réseau (LinkedIn, Insta, etc.)",
    )
    published = fields.Boolean(
        string="Publié",
        default=False,
        tracking=True,
        help="Coché manuellement par Anthony après publication réelle "
             "sur le réseau. Aucune publication automatique en V0.2.",
    )
    visual = fields.Image(string="Visuel principal", max_width=1920, max_height=1920)

    # Liens métier
    product_id = fields.Many2one(
        comodel_name="product.template",
        string="Produit lié",
        ondelete="set null",
    )
    project_id = fields.Many2one(
        comodel_name="project.project",
        string="Projet lié",
        ondelete="set null",
    )
    task_id = fields.Many2one(
        comodel_name="project.task",
        string="Tâche liée",
        ondelete="set null",
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Partenaire / Client lié",
        ondelete="set null",
        help="Lien optionnel (cas-client, témoignage). Pas de PII forcée.",
    )

    # Nouveaux liens V0.2
    idea_id = fields.Many2one(
        comodel_name="abrmd.grow.idea",
        string="Idée d'origine",
        ondelete="set null",
        help="Idée proposée (manuellement ou par cron) qui a donné lieu à ce post.",
    )
    pattern_ids = fields.Many2many(
        comodel_name="abrmd.grow.pattern",
        relation="abrmd_grow_post_pattern_rel",
        column1="post_id",
        column2="pattern_id",
        string="Patterns appliqués",
    )
    media_ids = fields.Many2many(
        comodel_name="abrmd.grow.media",
        relation="abrmd_grow_post_media_rel",
        column1="post_id",
        column2="media_id",
        string="Médias rattachés",
    )

    state = fields.Selection(
        selection=[
            ("draft", "Brouillon"),
            ("review", "À valider"),
            ("scheduled", "Programmé"),
            ("published", "Publié"),
            ("cancelled", "Annulé"),
        ],
        string="État",
        default="draft",
        tracking=True,
        required=True,
    )
    color = fields.Integer(string="Couleur Kanban")

    # IA
    generated_by_ai = fields.Boolean(
        string="Généré par Anthony Growth Agent",
        default=False,
        readonly=True,
    )
    ai_prompt = fields.Text(
        string="Prompt IA d'origine",
        readonly=True,
        help="Sauvegardé en lecture seule à des fins d'audit / replay.",
    )
    ai_model = fields.Char(
        string="Modèle IA utilisé",
        readonly=True,
        help="Ex. gpt-4o-mini, gpt-4o.",
    )
    ai_response_raw = fields.Text(
        string="Réponse IA brute (audit)",
        readonly=True,
    )
    ai_objectif = fields.Selection(
        selection=[
            ("lead", "Lead / Conversion"),
            ("awareness", "Notoriété"),
            ("sales", "Ventes"),
            ("engagement", "Engagement"),
        ],
        string="Objectif du post",
    )

    # Compteurs / contrôles
    char_count = fields.Integer(
        string="Caractères",
        compute="_compute_char_count",
        store=False,
    )
    char_limit_canal = fields.Integer(
        string="Limite canal",
        compute="_compute_char_limit",
        store=False,
    )
    over_limit = fields.Boolean(
        string="Dépasse la limite",
        compute="_compute_over_limit",
        store=False,
    )

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------
    @api.depends("content")
    def _compute_char_count(self):
        for rec in self:
            rec.char_count = len(rec.content or "")

    @api.depends("canal")
    def _compute_char_limit(self):
        for rec in self:
            rec.char_limit_canal = CHAR_LIMITS.get(rec.canal or "linkedin", 3000)

    @api.depends("content", "canal")
    def _compute_over_limit(self):
        for rec in self:
            limit = CHAR_LIMITS.get(rec.canal or "linkedin", 3000)
            rec.over_limit = len(rec.content or "") > limit

    # ------------------------------------------------------------------
    # Actions UI
    # ------------------------------------------------------------------
    def action_mark_published(self):
        for rec in self:
            rec.write({
                "published": True,
                "state": "published",
                "published_date": fields.Datetime.now(),
            })
        return True

    def action_send_to_review(self):
        for rec in self:
            rec.state = "review"
        return True

    def action_schedule(self):
        for rec in self:
            if not rec.scheduled_date:
                continue
            rec.state = "scheduled"
        return True

    def action_cancel(self):
        for rec in self:
            rec.state = "cancelled"
        return True

    def action_back_to_draft(self):
        for rec in self:
            rec.state = "draft"
        return True

    def action_regenerate_draft(self):
        """Ré-ouvre le wizard de génération en pré-remplissant avec les
        paramètres ayant servi à ce post (canal, idea, patterns, source)."""
        self.ensure_one()
        ctx = {
            "default_canal": self.canal,
            "default_idea_id": self.idea_id.id if self.idea_id else False,
            "default_pattern_ids": [(6, 0, self.pattern_ids.ids)],
            "default_product_id": self.product_id.id if self.product_id else False,
            "default_task_id": self.task_id.id if self.task_id else False,
            "default_project_id": self.project_id.id if self.project_id else False,
            "default_angle": (self.ai_prompt or "").split("Angle souhaité : ")[-1].split("\n")[0]
            if self.ai_prompt and "Angle souhaité" in (self.ai_prompt or "") else False,
            "default_objectif": self.ai_objectif or "lead",
            "default_source_post_id": self.id,
        }
        return {
            "type": "ir.actions.act_window",
            "name": _("Régénérer brouillon via Anthony Growth Agent"),
            "res_model": "abrmd.grow.generate.wizard",
            "view_mode": "form",
            "target": "new",
            "context": ctx,
        }

    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------
    @api.model
    def cron_check_due(self):
        """Cron quotidien — pour chaque post dont scheduled_date == today,
        crée une mail.activity de rappel pour Anthony (responsable du post)
        ou, à défaut, pour l'utilisateur admin.

        Aucune publication automatique : Anthony valide manuellement.
        """
        ICP = self.env["ir.config_parameter"].sudo()
        if ICP.get_param("abrmd_grow_marketing.killed", default="False") == "True":
            _logger.info("[abrmd_grow_marketing] kill switch actif — cron skip")
            return 0
        today = fields.Date.context_today(self)
        due = self.search([
            ("scheduled_date", "=", today),
            ("state", "in", ("scheduled", "review")),
            ("published", "=", False),
        ])
        if not due:
            return 0
        ActivityType = self.env.ref(
            "mail.mail_activity_data_todo", raise_if_not_found=False
        )
        admin = self.env.ref("base.user_admin", raise_if_not_found=False)
        notified = 0
        for post in due:
            try:
                post.activity_schedule(
                    activity_type_id=ActivityType.id if ActivityType else False,
                    summary=f"[Grow] Publier aujourd'hui : {post.title} ({post.canal})",
                    note=(post.content or "")[:500],
                    user_id=admin.id if admin else self.env.user.id,
                )
                notified += 1
            except Exception as exc:  # noqa: BLE001
                _logger.warning(
                    "[abrmd_grow_marketing] activity_schedule échec sur %s : %s",
                    post.id, exc,
                )
        _logger.info("[abrmd_grow_marketing] cron_check_due — %s posts notifiés", notified)
        return notified

    @api.model
    def build_ai_prompt(self, source_record=None, canal="linkedin", angle=None,
                        objectif=None, idea=None, patterns=None):
        """Construit un prompt structuré pour Anthony Growth Agent.

        Pure-python, sans appel HTTP — testable hors Odoo.
        ``source_record`` peut être un product.template ou project.task.
        ``idea`` est un abrmd.grow.idea, ``patterns`` un recordset
        abrmd.grow.pattern à appliquer.
        """
        parts = [
            "Tu es Anthony Growth Agent, copywriter B2B/B2C suisse du studio AB Intelligence Systèmes.",
            "Cible : décideurs PME suisses + indépendants tech-aware.",
            f"Génère un post éditorial pour le canal : {canal}.",
            f"Limite indicative de caractères : {CHAR_LIMITS.get(canal, 3000)}.",
        ]
        if objectif:
            parts.append(f"Objectif marketing : {objectif}.")
        if source_record is not None:
            name = getattr(source_record, "name", None) or getattr(
                source_record, "display_name", None
            ) or "(sans nom)"
            parts.append(f"Sujet / source : {name}")
            desc = getattr(source_record, "description_sale", None) or getattr(
                source_record, "description", None
            )
            if desc:
                parts.append(f"Contexte : {str(desc)[:500]}")
        if idea is not None and getattr(idea, "name", None):
            parts.append(f"Idée de départ : {idea.name}")
            if getattr(idea, "description", None):
                parts.append(f"Détails idée : {idea.description[:500]}")
        if patterns:
            try:
                pat_lines = []
                for p in patterns:
                    pat_lines.append(
                        f"- [{p.pattern_type}] {p.description[:120] if p.description else ''}"
                    )
                if pat_lines:
                    parts.append("Patterns à appliquer :")
                    parts.extend(pat_lines)
            except Exception:
                pass
        if angle:
            parts.append(f"Angle souhaité : {angle}")
        parts.append(
            "Format : 1 post court, ton RMD Store (Apple reconditionné, B2B/B2C, suisse). "
            "Hook fort dans les 3 premières secondes. CTA clair à la fin. "
            "Aucun emoji sauf si le canal s'y prête (Insta, TikTok)."
        )
        return "\n".join(parts)

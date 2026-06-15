# -*- coding: utf-8 -*-
"""Wizard de génération de vidéo MP4 à partir d'un post.

Flux :
1. Anthony ouvre le wizard depuis un post Grow (ou direct depuis le menu).
2. Renseigne : médias à utiliser, format, voix, durée max.
3. action_create_video() crée un abrmd.grow.video en state 'generating'.
4. Le cron `cron_process_pending_videos` traite la vidéo en arrière-plan.
"""
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AbrmdGrowVideoWizard(models.TransientModel):
    _name = "abrmd.grow.video.wizard"
    _description = "Wizard — Générer une vidéo Grow Marketing"

    post_id = fields.Many2one(
        "abrmd.grow.post",
        string="Post associé",
        required=True,
    )
    name = fields.Char(string="Nom de la vidéo", required=True)
    script = fields.Text(
        string="Script (voix off + sous-titres)",
        required=True,
        help="Sera lu par la voix off et utilisé pour les sous-titres.",
    )
    media_ids = fields.Many2many(
        "abrmd.grow.media",
        relation="abrmd_grow_video_wizard_media_rel",
        column1="wizard_id",
        column2="media_id",
        string="Médias à utiliser",
    )
    format = fields.Selection(
        selection=[
            ("9_16", "9:16 (TikTok / Reels / Shorts)"),
            ("16_9", "16:9 (YouTube classique)"),
            ("1_1", "1:1 (Instagram feed)"),
            ("4_5", "4:5 (Instagram portrait)"),
        ],
        string="Format",
        default="9_16",
        required=True,
    )
    voice_id = fields.Selection(
        selection=[
            ("nova", "Nova (féminine, énergique)"),
            ("alloy", "Alloy (neutre)"),
            ("echo", "Echo (masculine)"),
            ("fable", "Fable (britannique)"),
            ("onyx", "Onyx (grave)"),
            ("shimmer", "Shimmer (douce)"),
        ],
        string="Voix off",
        default="nova",
    )
    max_duration_s = fields.Integer(string="Durée max (sec)", default=45)
    burn_subtitles = fields.Boolean(string="Sous-titres burnés", default=True)
    add_intro = fields.Boolean(string="Intro brandée", default=False)
    add_outro = fields.Boolean(string="Outro brandée", default=False)
    cost_estimate_eur = fields.Float(
        string="Coût estimé (€)",
        compute="_compute_cost_estimate",
        digits=(8, 4),
    )
    start_immediately = fields.Boolean(
        string="Démarrer immédiatement",
        default=True,
        help="Si coché, la vidéo passe en state 'generating' et sera "
             "traitée au prochain run du cron. Sinon, reste en 'draft'.",
    )

    @api.depends("script", "voice_id", "max_duration_s")
    def _compute_cost_estimate(self):
        Pipeline = self.env["abrmd.grow.video.pipeline"]
        for rec in self:
            rec.cost_estimate_eur = Pipeline.estimate_cost(
                rec.script or "",
                voice_provider="openai_tts",
                duration_s=rec.max_duration_s or 30,
            )

    def action_create_video(self):
        self.ensure_one()
        if not self.script:
            raise UserError(_("Script vide. Renseigne le texte à lire."))
        Video = self.env["abrmd.grow.video"]
        video = Video.create({
            "name": self.name,
            "post_id": self.post_id.id,
            "script": self.script,
            "media_ids": [(6, 0, self.media_ids.ids)],
            "format": self.format,
            "voice_provider": "openai_tts",
            "voice_id": self.voice_id,
            "max_duration_s": self.max_duration_s,
            "burn_subtitles": self.burn_subtitles,
            "add_intro": self.add_intro,
            "add_outro": self.add_outro,
            "state": "generating" if self.start_immediately else "draft",
            "started_at": fields.Datetime.now() if self.start_immediately else False,
        })
        return {
            "type": "ir.actions.act_window",
            "name": _("Vidéo Grow"),
            "res_model": "abrmd.grow.video",
            "res_id": video.id,
            "view_mode": "form",
            "target": "current",
        }

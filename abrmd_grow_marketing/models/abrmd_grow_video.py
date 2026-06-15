# -*- coding: utf-8 -*-
"""Modèle abrmd.grow.video — vidéo MP4 générée à partir d'un post.

Workflow :
1. draft       — record créé, paramètres définis
2. generating  — pipeline en cours (TTS + Whisper + FFmpeg)
3. ready       — MP4 produit, attaché à output_file
4. failed      — erreur (voir error_message)

La génération est asynchrone : un cron `cron_process_pending_videos`
prend les vidéos en state 'generating' et les traite.

Coût visé : ~0,05€ par vidéo (OpenAI TTS + Whisper, FFmpeg gratuit).
"""
import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


FORMAT_SELECTION = [
    ("9_16", "9:16 (TikTok / Reels / Shorts)"),
    ("16_9", "16:9 (YouTube classique)"),
    ("1_1", "1:1 (Instagram feed)"),
    ("4_5", "4:5 (Instagram portrait)"),
]

VOICE_PROVIDER = [
    ("openai_tts", "OpenAI TTS (low-cost)"),
    ("elevenlabs", "ElevenLabs (V0.3)"),
    ("none", "Sans voix off"),
]

# Voix OpenAI TTS disponibles
OPENAI_VOICES = [
    ("nova", "Nova (féminine, énergique)"),
    ("alloy", "Alloy (neutre, claire)"),
    ("echo", "Echo (masculine, posée)"),
    ("fable", "Fable (britannique, chaleureuse)"),
    ("onyx", "Onyx (masculine grave)"),
    ("shimmer", "Shimmer (féminine douce)"),
]


class AbrmdGrowVideo(models.Model):
    _name = "abrmd.grow.video"
    _description = "Vidéo MP4 Grow Marketing (low-cost)"
    _order = "create_date desc, id desc"
    _inherit = ["mail.thread"]

    name = fields.Char(string="Nom", required=True, tracking=True)
    post_id = fields.Many2one(
        comodel_name="abrmd.grow.post",
        string="Post associé",
        ondelete="cascade",
        tracking=True,
    )
    media_ids = fields.Many2many(
        comodel_name="abrmd.grow.media",
        relation="abrmd_grow_video_media_rel",
        column1="video_id",
        column2="media_id",
        string="Médias sources (images / clips)",
    )
    script = fields.Text(
        string="Script (voix off)",
        help="Texte qui sera lu par la voix off et burné en sous-titres.",
    )

    # Voix
    voice_provider = fields.Selection(
        selection=VOICE_PROVIDER,
        string="Provider voix",
        default="openai_tts",
    )
    voice_id = fields.Selection(
        selection=OPENAI_VOICES,
        string="Voix",
        default="nova",
    )
    voiceover_file = fields.Binary(
        string="Voix off (MP3)",
        attachment=True,
        readonly=True,
    )
    voiceover_filename = fields.Char(string="Nom fichier voix off", readonly=True)

    # Transcription
    subtitles_srt = fields.Text(
        string="Sous-titres (SRT)",
        readonly=True,
    )

    # Sortie
    output_file = fields.Binary(
        string="Vidéo MP4",
        attachment=True,
        readonly=True,
    )
    output_filename = fields.Char(string="Nom fichier MP4", readonly=True)
    duration_s = fields.Float(string="Durée (sec)", readonly=True)

    # Configuration
    format = fields.Selection(
        selection=FORMAT_SELECTION,
        string="Format",
        default="9_16",
        required=True,
    )
    max_duration_s = fields.Integer(
        string="Durée max (sec)",
        default=60,
        help="Limite dure : la pipeline coupe la vidéo si dépassement.",
    )
    add_intro = fields.Boolean(string="Intro brandée RMD/AB-Intelligence", default=True)
    add_outro = fields.Boolean(string="Outro brandée", default=True)
    burn_subtitles = fields.Boolean(string="Sous-titres burnés", default=True)

    # État
    state = fields.Selection(
        selection=[
            ("draft", "Brouillon"),
            ("generating", "Génération en cours"),
            ("ready", "Prête"),
            ("failed", "Échec"),
        ],
        string="État",
        default="draft",
        tracking=True,
        required=True,
    )
    error_message = fields.Text(string="Message d'erreur", readonly=True)
    cost_estimate_eur = fields.Float(
        string="Coût estimé (€)",
        compute="_compute_cost_estimate",
        store=True,
        digits=(8, 4),
    )

    # Métadonnées techniques
    pipeline_log = fields.Text(string="Log pipeline (debug)", readonly=True)
    started_at = fields.Datetime(string="Démarrage pipeline", readonly=True)
    finished_at = fields.Datetime(string="Fin pipeline", readonly=True)

    @api.depends("script", "voice_provider", "duration_s")
    def _compute_cost_estimate(self):
        """Estimation pure-python du coût en euros.

        Tarifs indicatifs (mai 2026, hors Anthropic) :
        - OpenAI TTS : ~0.015 USD / 1k chars (~0.014€)
        - Whisper : ~0.006 USD / minute (~0.0055€)
        """
        for rec in self:
            chars = len(rec.script or "")
            duration_min = max(1.0, (rec.duration_s or 30.0)) / 60.0
            tts_cost = 0.0
            if rec.voice_provider == "openai_tts":
                tts_cost = (chars / 1000.0) * 0.014
            elif rec.voice_provider == "elevenlabs":
                # ElevenLabs ~0.30$/1k chars sur le plan Pro
                tts_cost = (chars / 1000.0) * 0.27
            whisper_cost = duration_min * 0.0055
            rec.cost_estimate_eur = round(tts_cost + whisper_cost, 4)

    # ------------------------------------------------------------------
    # Actions UI
    # ------------------------------------------------------------------
    def action_start_pipeline(self):
        """Marque la vidéo comme à traiter. Le cron la prendra en charge."""
        for rec in self:
            if not rec.script:
                from odoo.exceptions import UserError
                raise UserError(_("Script vide. Renseigne le texte à lire."))
            rec.write({
                "state": "generating",
                "started_at": fields.Datetime.now(),
                "error_message": False,
            })
        return True

    def action_process_now(self):
        """Lance le pipeline immédiatement (synchrone — bloquant !).

        À utiliser pour debug seulement. En prod, laisse le cron tourner.
        """
        Pipeline = self.env["abrmd.grow.video.pipeline"]
        for rec in self:
            Pipeline._run_pipeline(rec)
        return True

    def action_retry(self):
        for rec in self:
            rec.write({
                "state": "generating",
                "error_message": False,
                "started_at": fields.Datetime.now(),
            })
        return True

    def action_attach_to_post(self):
        """Attache le MP4 au post comme média rattaché."""
        self.ensure_one()
        if not self.output_file or not self.post_id:
            return False
        Media = self.env["abrmd.grow.media"]
        media = Media.create({
            "name": self.output_filename or self.name,
            "filename": self.output_filename or (self.name + ".mp4"),
            "file": self.output_file,
            "mimetype": "video/mp4",
            "source": "library",
        })
        self.post_id.write({
            "media_ids": [(4, media.id)],
        })
        return {
            "type": "ir.actions.act_window",
            "name": _("Post mis à jour"),
            "res_model": "abrmd.grow.post",
            "res_id": self.post_id.id,
            "view_mode": "form",
            "target": "current",
        }

    # ------------------------------------------------------------------
    # Cron
    # ------------------------------------------------------------------
    @api.model
    def cron_process_pending_videos(self):
        """Cron : traite les vidéos en state 'generating'.

        Une seule vidéo à la fois pour éviter de surcharger FFmpeg.
        """
        ICP = self.env["ir.config_parameter"].sudo()
        if ICP.get_param("abrmd_grow_marketing.killed", default="False") == "True":
            return 0
        pending = self.search([("state", "=", "generating")], limit=1)
        if not pending:
            return 0
        Pipeline = self.env["abrmd.grow.video.pipeline"]
        Pipeline._run_pipeline(pending)
        return 1

# -*- coding: utf-8 -*-
"""Modèle abrmd.grow.media — bibliothèque médias (visuels, vidéos).

Sources possibles :
- icloud : importé depuis un dossier iCloud Drive local (instance self-hosted seulement)
- drive  : Google Drive (OAuth — V0.3, stub en V0.2)
- photos : Google Photos (V0.3, stub en V0.2)
- upload : upload manuel via formulaire Odoo (compatible SaaS)

Stockage : soit binaire (file), soit lien externe (file_url), soit les deux.
"""
import base64
import logging
import os

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


SOURCE_SELECTION = [
    ("upload", "Upload manuel"),
    ("icloud", "iCloud Drive (local)"),
    ("drive", "Google Drive"),
    ("photos", "Google Photos"),
    ("library", "Bibliothèque interne"),
]


class AbrmdGrowMedia(models.Model):
    _name = "abrmd.grow.media"
    _description = "Média (visuel / vidéo) Grow Marketing"
    _order = "create_date desc, id desc"
    _inherit = ["mail.thread"]

    name = fields.Char(string="Nom", required=True, tracking=True)
    file = fields.Binary(
        string="Fichier",
        attachment=True,
        help="Stockage interne Odoo (visible partout). Préférer pour les "
             "visuels < 5 MB et instances SaaS.",
    )
    filename = fields.Char(string="Nom de fichier d'origine")
    file_url = fields.Char(
        string="URL / chemin externe",
        help="Lien externe (iCloud public link, Drive, S3) si pas stocké en binary.",
    )
    mimetype = fields.Char(string="Type MIME")
    size_kb = fields.Integer(string="Taille (KB)", readonly=True)
    is_image = fields.Boolean(
        string="Est une image",
        compute="_compute_is_image",
        store=True,
    )
    is_video = fields.Boolean(
        string="Est une vidéo",
        compute="_compute_is_video",
        store=True,
    )
    thumbnail = fields.Image(
        string="Vignette",
        max_width=400,
        max_height=400,
    )
    source = fields.Selection(
        selection=SOURCE_SELECTION,
        string="Source",
        default="upload",
        required=True,
        tracking=True,
    )
    tag_ids = fields.Many2many(
        comodel_name="abrmd.grow.tag",
        relation="abrmd_grow_media_tag_rel",
        column1="media_id",
        column2="tag_id",
        string="Tags",
    )
    product_ids = fields.Many2many(
        comodel_name="product.template",
        relation="abrmd_grow_media_product_rel",
        column1="media_id",
        column2="product_id",
        string="Produits liés",
    )
    notes = fields.Text(string="Notes internes")
    color = fields.Integer(string="Couleur Kanban")

    # Stats utilisation
    post_ids = fields.Many2many(
        comodel_name="abrmd.grow.post",
        relation="abrmd_grow_post_media_rel",
        column1="media_id",
        column2="post_id",
        string="Posts utilisant ce média",
    )
    usage_count = fields.Integer(
        string="Utilisations",
        compute="_compute_usage_count",
    )

    @api.depends("post_ids")
    def _compute_usage_count(self):
        for rec in self:
            rec.usage_count = len(rec.post_ids)

    @api.depends("mimetype")
    def _compute_is_image(self):
        for rec in self:
            rec.is_image = bool(rec.mimetype and rec.mimetype.startswith("image/"))

    @api.depends("mimetype")
    def _compute_is_video(self):
        for rec in self:
            rec.is_video = bool(rec.mimetype and rec.mimetype.startswith("video/"))

    # ------------------------------------------------------------------
    # Helpers pure-python
    # ------------------------------------------------------------------
    @staticmethod
    def guess_mimetype(filename):
        if not filename:
            return ""
        lower = filename.lower()
        if lower.endswith((".jpg", ".jpeg")):
            return "image/jpeg"
        if lower.endswith(".png"):
            return "image/png"
        if lower.endswith(".gif"):
            return "image/gif"
        if lower.endswith(".webp"):
            return "image/webp"
        if lower.endswith(".heic"):
            return "image/heic"
        if lower.endswith(".mp4"):
            return "video/mp4"
        if lower.endswith(".mov"):
            return "video/quicktime"
        if lower.endswith(".webm"):
            return "video/webm"
        return "application/octet-stream"

    @api.model
    def create(self, vals):
        # Détection mimetype automatique
        if vals.get("filename") and not vals.get("mimetype"):
            vals["mimetype"] = self.guess_mimetype(vals["filename"])
        # Taille en KB si on a un binary
        if vals.get("file") and not vals.get("size_kb"):
            try:
                raw = base64.b64decode(vals["file"])
                vals["size_kb"] = len(raw) // 1024
            except Exception:
                pass
        return super().create(vals)


class AbrmdGrowMediaImportWizard(models.TransientModel):
    """Wizard : importer un dossier iCloud Drive local (instance self-hosted).

    Sur SaaS / Odoo Online : ce wizard échoue car pas d'accès filesystem hôte.
    Anthony doit alors utiliser le wizard UploadBatch (drag-and-drop).
    """
    _name = "abrmd.grow.media.import.wizard"
    _description = "Wizard — import média depuis dossier local (iCloud Drive)"

    folder_path = fields.Char(
        string="Chemin du dossier à scanner",
        required=True,
        help="Ex. /Users/anthony/Library/Mobile Documents/com~apple~CloudDocs/RMD-AB-Knowledge/Media/Grow-Marketing/",
    )
    recursive = fields.Boolean(string="Récursif (sous-dossiers inclus)", default=True)
    max_files = fields.Integer(string="Max fichiers à importer", default=200)
    tag_ids = fields.Many2many(
        comodel_name="abrmd.grow.tag",
        string="Tags à appliquer",
    )
    imported_count = fields.Integer(string="Importés", readonly=True)
    skipped_count = fields.Integer(string="Ignorés (taille ou type)", readonly=True)

    ALLOWED_EXT = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic",
                   ".mp4", ".mov", ".webm")
    MAX_SIZE_MB = 50

    def action_import(self):
        self.ensure_one()
        if not self.folder_path or not os.path.isdir(self.folder_path):
            raise UserError(_(
                "Dossier introuvable : %s.\n\nSur Odoo SaaS (Online), "
                "le filesystem hôte n'est pas accessible : utilise le "
                "wizard Upload manuel à la place."
            ) % (self.folder_path or "(vide)"))
        Media = self.env["abrmd.grow.media"]
        imported = 0
        skipped = 0
        for root, dirs, files in os.walk(self.folder_path):
            for fname in files:
                if imported >= (self.max_files or 200):
                    break
                if not fname.lower().endswith(self.ALLOWED_EXT):
                    skipped += 1
                    continue
                fpath = os.path.join(root, fname)
                try:
                    size = os.path.getsize(fpath)
                    if size > self.MAX_SIZE_MB * 1024 * 1024:
                        skipped += 1
                        continue
                    with open(fpath, "rb") as f:
                        raw = f.read()
                    Media.create({
                        "name": fname,
                        "filename": fname,
                        "file": base64.b64encode(raw),
                        "mimetype": Media.guess_mimetype(fname),
                        "size_kb": size // 1024,
                        "source": "icloud",
                        "tag_ids": [(6, 0, self.tag_ids.ids)] if self.tag_ids else False,
                    })
                    imported += 1
                except Exception as exc:  # noqa: BLE001
                    _logger.warning(
                        "[abrmd_grow_marketing] import média %s échec : %s",
                        fpath, exc,
                    )
                    skipped += 1
            if not self.recursive:
                break
        self.imported_count = imported
        self.skipped_count = skipped
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

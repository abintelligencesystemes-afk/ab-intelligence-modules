# -*- coding: utf-8 -*-
"""Settings page — OpenAI key, modèle GPT, kill switch, control plane."""
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    abrmd_grow_enabled = fields.Boolean(
        string="Activer Grow Marketing",
        config_parameter="abrmd_grow_marketing.enabled",
        default=True,
    )
    abrmd_grow_openai_api_key = fields.Char(
        string="Clé API OpenAI (Anthony Growth Agent)",
        config_parameter="openai.api_key",
        help="Clé API OpenAI utilisée par le wizard de génération de post. "
             "Stockée dans ir.config_parameter. À protéger via chiffrement "
             "filestore ou variable d'env hébergeur. Ne JAMAIS commit en clair.",
    )
    abrmd_grow_openai_model = fields.Char(
        string="Modèle GPT (ex. gpt-4o-mini)",
        config_parameter="abrmd_grow_marketing.openai_model",
        default="gpt-4o-mini",
    )
    abrmd_grow_custom_gpt_url = fields.Char(
        string="URL Custom GPT Anthony Growth Agent",
        config_parameter="abrmd_grow_marketing.custom_gpt_url",
        default="https://chatgpt.com/g/g-6a00b8f103b48191bdf2588df911e72a",
        help="Référence informationnelle (le custom GPT n'est pas appelable "
             "directement via API ; la clé OpenAI est utilisée avec un system "
             "prompt équivalent côté wizard).",
    )
    abrmd_grow_control_plane_url = fields.Char(
        string="URL abi-control-plane",
        config_parameter="abrmd_grow_marketing.control_plane_url",
        default="https://abi-control.rmd-store.com/v1",
    )
    abrmd_grow_killed = fields.Boolean(
        string="Kill switch (désactive le module)",
        config_parameter="abrmd_grow_marketing.killed",
        default=False,
    )

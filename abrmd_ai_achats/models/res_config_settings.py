# -*- coding: utf-8 -*-
"""
Configuration du module (Settings → AI Achats).

Champs exposés :
- URL du Worker abi-control-plane
- License JWT du module
- Instance UUID
- Seuils signature/produit
- Killed switch (désactivation immédiate)
"""
from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    abrmd_ai_achats_enabled = fields.Boolean(
        string="Activer AI Achats",
        config_parameter="abrmd_ai_achats.enabled",
        default=True,
    )
    abrmd_ai_achats_worker_url = fields.Char(
        string="URL Worker OCR",
        config_parameter="abrmd_ai_achats.worker_url",
        default="https://abi-control-plane.workers.dev/api/ocr/invoice",
        help="Endpoint du Cloudflare Worker qui proxy OpenAI Vision.",
    )
    abrmd_ai_achats_license_key = fields.Char(
        string="License Key JWT",
        config_parameter="abrmd_ai_achats.license_key",
        help="JWT émis par Stripe checkout / control plane.",
    )
    abrmd_ai_achats_instance_uuid = fields.Char(
        string="Instance UUID",
        config_parameter="abrmd_ai_achats.instance_uuid",
        help="UUID v4 unique de cette instance Odoo.",
    )
    abrmd_ai_achats_signature_threshold = fields.Float(
        string="Seuil signature fournisseur",
        config_parameter="abrmd_ai_achats.signature_threshold",
        default=0.8,
        help="Score minimum (0..1) pour considérer une signature comme match.",
    )
    abrmd_ai_achats_product_match_threshold = fields.Float(
        string="Seuil matching produit",
        config_parameter="abrmd_ai_achats.product_match_threshold",
        default=0.8,
    )
    abrmd_ai_achats_killed = fields.Boolean(
        string="Mode kill (désactive tous les appels)",
        config_parameter="abrmd_ai_achats.killed",
        default=False,
        help="Si coché : aucun appel OCR n'est tenté, on retourne une erreur immédiate.",
    )
    abrmd_ai_achats_model = fields.Char(
        string="Modèle OpenAI",
        config_parameter="abrmd_ai_achats.openai_model",
        default="gpt-4o",
    )
    abrmd_ai_achats_timeout_sec = fields.Integer(
        string="Timeout HTTP (s)",
        config_parameter="abrmd_ai_achats.http_timeout_sec",
        default=60,
    )

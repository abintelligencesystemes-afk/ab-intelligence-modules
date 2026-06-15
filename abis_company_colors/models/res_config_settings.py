# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    abis_color_primary = fields.Char(
        related="company_id.abis_color_primary", readonly=False
    )
    abis_color_secondary = fields.Char(
        related="company_id.abis_color_secondary", readonly=False
    )
    abis_color_accent = fields.Char(
        related="company_id.abis_color_accent", readonly=False
    )
    abis_colors_active = fields.Boolean(
        related="company_id.abis_colors_active", readonly=False
    )

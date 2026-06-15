# -*- coding: utf-8 -*-
"""Ajoute 3 couleurs corporate configurables par compagnie."""
import re

from odoo import api, fields, models
from odoo.exceptions import ValidationError

HEX_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}){1,2}$")


class ResCompany(models.Model):
    _inherit = "res.company"

    abis_color_primary = fields.Char(
        string="Couleur principale",
        default="#714B67",
        help="Couleur des boutons primaires, liens actifs, en-tête portail.",
    )
    abis_color_secondary = fields.Char(
        string="Couleur secondaire",
        default="#017E84",
        help="Couleur secondaire : hover, focus, boutons d'accompagnement.",
    )
    abis_color_accent = fields.Char(
        string="Couleur d'accentuation",
        default="#F2C641",
        help="Badges, alertes positives, mise en valeur ponctuelle.",
    )
    abis_colors_active = fields.Boolean(
        string="Activer les couleurs corporate",
        default=True,
        help="Désactive pour revenir aux couleurs Odoo par défaut sans désinstaller.",
    )

    @api.constrains(
        "abis_color_primary", "abis_color_secondary", "abis_color_accent"
    )
    def _check_hex_colors(self):
        for company in self:
            for fname in (
                "abis_color_primary",
                "abis_color_secondary",
                "abis_color_accent",
            ):
                value = company[fname] or ""
                if value and not HEX_RE.match(value):
                    raise ValidationError(
                        "La couleur '%s' doit être au format hexadécimal "
                        "(ex: #714B67 ou #abc). Valeur reçue : %s"
                        % (fname, value)
                    )

    def get_abis_css(self):
        """Retourne le CSS à servir pour cette compagnie."""
        self.ensure_one()
        if not self.abis_colors_active:
            return "/* abis_company_colors : désactivé */"
        return (
            ":root, .o_portal {\n"
            "  --abis-color-primary: %s;\n"
            "  --abis-color-secondary: %s;\n"
            "  --abis-color-accent: %s;\n"
            "}\n"
            ".o_portal .btn-primary, .o_portal a.btn-primary {\n"
            "  background-color: var(--abis-color-primary);\n"
            "  border-color: var(--abis-color-primary);\n"
            "}\n"
            ".o_portal .btn-secondary {\n"
            "  background-color: var(--abis-color-secondary);\n"
            "  border-color: var(--abis-color-secondary);\n"
            "}\n"
            ".o_portal .badge-accent { background-color: var(--abis-color-accent); }\n"
            % (
                self.abis_color_primary or "#714B67",
                self.abis_color_secondary or "#017E84",
                self.abis_color_accent or "#F2C641",
            )
        )

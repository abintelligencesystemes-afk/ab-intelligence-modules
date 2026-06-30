# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    abrmd_rgpd_dpo_name = fields.Char(
        string="Nom du DPO",
        config_parameter="abrmd_ai_rgpd.dpo_name",
        help="Nom du Délégué à la Protection des Données (Article 37 RGPD).",
    )
    abrmd_rgpd_dpo_email = fields.Char(
        string="Email du DPO",
        config_parameter="abrmd_ai_rgpd.dpo_email",
        help="Adresse de contact du DPO publique (Article 37).",
    )
    abrmd_rgpd_dpo_phone = fields.Char(
        string="Téléphone du DPO",
        config_parameter="abrmd_ai_rgpd.dpo_phone",
    )
    abrmd_rgpd_retention_default_days = fields.Integer(
        string="Rétention par défaut (jours)",
        default=1095,  # 3 ans
        config_parameter="abrmd_ai_rgpd.retention_default_days",
        help="Durée de conservation par défaut des données personnelles, en jours.",
    )
    abrmd_rgpd_request_default_deadline_days = fields.Integer(
        string="Délai légal demande (jours)",
        default=30,
        config_parameter="abrmd_ai_rgpd.request_default_deadline_days",
        help="Délai légal de réponse à une demande de droits RGPD (Art.12). Maximum 1 mois prolongeable de 2 mois si complexité justifiée.",
    )
    abrmd_rgpd_telemetry_enabled = fields.Boolean(
        string="Activer télémétrie AB Intelligence (opt-in)",
        config_parameter="abrmd_ai_rgpd.telemetry_enabled",
        help="Envoie des compteurs anonymisés au control plane AB Intelligence pour mesurer l'usage. Aucune donnée personnelle.",
    )
    abrmd_rgpd_anonymization_salt = fields.Char(
        string="Sel d'anonymisation",
        config_parameter="abrmd_ai_rgpd.anonymization_salt",
        help="Sel SHA-256 utilisé pour la pseudonymisation. Garde-le secret. Sert à rendre le hash non rejouable cross-tenant.",
    )

    @api.model
    def get_dpo_contact(self):
        params = self.env["ir.config_parameter"].sudo()
        return {
            "name": params.get_param("abrmd_ai_rgpd.dpo_name", ""),
            "email": params.get_param("abrmd_ai_rgpd.dpo_email", ""),
            "phone": params.get_param("abrmd_ai_rgpd.dpo_phone", ""),
        }

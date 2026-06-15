# -*- coding: utf-8 -*-
"""Pilier 1 — Registre des activités de traitement (Article 30 RGPD).

Chaque entrée représente UN traitement de données personnelles dans l'organisation.
Le registre est obligatoire pour toute structure de plus de 250 employés OU
quand le traitement n'est pas occasionnel OU porte sur des données sensibles
ou des condamnations.
"""
from odoo import api, fields, models


class AbrmdRgpdRegistre(models.Model):
    _name = "abrmd.rgpd.registre"
    _description = "Registre RGPD Art.30 — Activité de traitement"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "sequence, name"

    name = fields.Char(string="Nom du traitement", required=True, tracking=True)
    sequence = fields.Integer(default=10)
    code = fields.Char(string="Code interne", tracking=True, help="Référence interne (ex: TRT-001).")
    active = fields.Boolean(default=True)

    # 1. Identité du responsable de traitement
    controller_name = fields.Char(string="Responsable de traitement", required=True, tracking=True)
    controller_email = fields.Char(string="Email du responsable", required=True)
    controller_address = fields.Text(string="Adresse du responsable")

    # 2. Finalités du traitement
    purpose = fields.Text(
        string="Finalité du traitement",
        required=True,
        tracking=True,
        help="Description claire de l'objectif (ex: gestion des commandes clients).",
    )
    legal_basis = fields.Selection(
        [
            ("consent", "Consentement (Art.6.1.a)"),
            ("contract", "Exécution d'un contrat (Art.6.1.b)"),
            ("legal_obligation", "Obligation légale (Art.6.1.c)"),
            ("vital_interest", "Intérêt vital (Art.6.1.d)"),
            ("public_interest", "Intérêt public (Art.6.1.e)"),
            ("legitimate_interest", "Intérêt légitime (Art.6.1.f)"),
        ],
        string="Base légale (Art.6)",
        required=True,
        tracking=True,
    )

    # 3. Catégories de personnes
    data_subjects = fields.Char(
        string="Catégories de personnes",
        required=True,
        help="Ex: clients, prospects, salariés, fournisseurs.",
    )

    # 4. Catégories de données
    data_categories = fields.Text(
        string="Catégories de données collectées",
        required=True,
        help="Ex: identité, contact, données bancaires, données de connexion.",
    )
    data_sensitive = fields.Boolean(
        string="Données sensibles (Art.9)",
        help="Données de santé, origine ethnique, opinions politiques, etc.",
    )
    data_minors = fields.Boolean(
        string="Concerne des mineurs",
    )

    # 5. Destinataires
    recipients = fields.Text(string="Destinataires des données")
    recipients_third_country = fields.Boolean(
        string="Transfert hors UE",
        help="Cocher si données transférées hors EEE.",
    )
    transfer_safeguards = fields.Char(
        string="Garanties transfert hors UE",
        help="Clauses contractuelles types, BCR, décision d'adéquation, etc.",
    )

    # 6. Durée de conservation
    retention_days = fields.Integer(
        string="Durée de conservation (jours)",
        required=True,
        default=1095,  # 3 ans par défaut
        help="Durée maximale de conservation des données personnelles.",
    )
    retention_legal_ref = fields.Char(
        string="Référence légale de la durée",
        help="Ex: Code de commerce L123-22, durée comptable 10 ans.",
    )

    # 7. Mesures de sécurité
    security_measures = fields.Text(
        string="Mesures de sécurité (Art.32)",
        help="Description des mesures techniques et organisationnelles.",
    )

    # Computed
    consent_ids = fields.One2many(
        "abrmd.rgpd.consent", "registre_id", string="Consentements liés"
    )
    consent_count = fields.Integer(
        string="Consentements", compute="_compute_consent_count"
    )

    @api.depends("consent_ids")
    def _compute_consent_count(self):
        for rec in self:
            rec.consent_count = len(rec.consent_ids)

    _sql_constraints = [
        ("uniq_code", "UNIQUE(code)", "Le code interne doit être unique."),
    ]

    def action_view_consents(self):
        self.ensure_one()
        return {
            "name": "Consentements — %s" % self.name,
            "type": "ir.actions.act_window",
            "res_model": "abrmd.rgpd.consent",
            "view_mode": "list,form",
            "domain": [("registre_id", "=", self.id)],
            "context": {"default_registre_id": self.id},
        }

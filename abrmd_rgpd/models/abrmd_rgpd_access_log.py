# -*- coding: utf-8 -*-
"""Pilier 5 — Logs d'accès aux données sensibles (Art.30 + Art.32 RGPD).

Trace toutes les opérations d'accès, modification, export, anonymisation
sur des données personnelles, pour audit DPO et démonstration de conformité.
"""
from odoo import api, fields, models


class AbrmdRgpdAccessLog(models.Model):
    _name = "abrmd.rgpd.access.log"
    _description = "Log d'accès RGPD"
    _order = "create_date desc, id desc"
    _rec_name = "action_description"

    log_type = fields.Selection(
        [
            ("read", "Consultation"),
            ("write", "Modification"),
            ("create", "Création"),
            ("unlink", "Suppression"),
            ("export", "Export de données"),
            ("anonymization", "Anonymisation"),
            ("pseudonymization", "Pseudonymisation"),
            ("right_access", "Droit d'accès exercé"),
            ("right_erasure", "Droit à l'effacement exercé"),
            ("right_portability", "Droit à la portabilité exercé"),
            ("other", "Autre"),
        ],
        string="Type d'opération",
        required=True,
        index=True,
    )

    model_id = fields.Many2one("ir.model", string="Modèle technique", ondelete="set null")
    model_name = fields.Char(related="model_id.model", store=True, index=True)
    res_id = fields.Integer(string="ID enregistrement", index=True)

    # Sujet (pseudonymisé)
    subject_hash = fields.Char(
        string="Hash du sujet (SHA-256)",
        index=True,
        help="Pseudonyme du sujet — permet de retrouver TOUS les accès à ses données sans stocker son identité.",
    )

    # Action et acteur
    action_description = fields.Char(string="Description", required=True)
    executed_by = fields.Many2one("res.users", string="Utilisateur acteur", ondelete="set null")
    executed_for = fields.Many2one(
        "abrmd.rgpd.request",
        string="Demande RGPD liée",
        ondelete="set null",
        help="Si l'accès était lié à une demande d'exercice de droit.",
    )

    # Trace technique
    ip_address = fields.Char(
        string="IP source (anonymisée)",
        help="IP anonymisée /24 pour IPv4, /48 pour IPv6.",
    )
    legal_basis = fields.Selection(
        [
            ("consent", "Consentement"),
            ("contract", "Contrat"),
            ("legal_obligation", "Obligation légale"),
            ("vital_interest", "Intérêt vital"),
            ("public_interest", "Intérêt public"),
            ("legitimate_interest", "Intérêt légitime"),
            ("right_exercise", "Exercice d'un droit"),
        ],
        string="Base légale invoquée",
    )

    sensitive = fields.Boolean(
        string="Donnée sensible (Art.9)",
        help="Cocher si l'accès porte sur des données de santé, opinions politiques, etc.",
    )

    @api.model
    def log_access(self, model, res_id, log_type, description, subject_hash=False, legal_basis=False, sensitive=False, request_id=False):
        """API publique — à appeler depuis n'importe quel modèle pour tracer un accès.

        Exemple :
            self.env["abrmd.rgpd.access.log"].sudo().log_access(
                model="res.partner",
                res_id=partner.id,
                log_type="export",
                description="Export CSV pour le client portail",
                subject_hash=hash_email(partner.email),
                legal_basis="contract",
            )
        """
        model_rec = self.env["ir.model"].sudo().search([("model", "=", model)], limit=1)
        return self.sudo().create({
            "log_type": log_type,
            "model_id": model_rec.id if model_rec else False,
            "res_id": res_id,
            "action_description": description,
            "subject_hash": subject_hash,
            "legal_basis": legal_basis,
            "sensitive": sensitive,
            "executed_by": self.env.uid,
            "executed_for": request_id,
        })

    @api.model
    def _cron_gc_old_logs(self):
        """Cron quotidien — purge les logs d'accès au-delà de la rétention configurée.

        Note : ne purge JAMAIS les logs liés à une demande RGPD (preuve de conformité à conserver).
        """
        params = self.env["ir.config_parameter"].sudo()
        days = int(params.get_param("abrmd_ai_rgpd.access_log_retention_days", 1825))  # 5 ans par défaut
        threshold = fields.Datetime.subtract(fields.Datetime.now(), days=days)
        old_logs = self.search([
            ("create_date", "<", threshold),
            ("executed_for", "=", False),
        ])
        count = len(old_logs)
        old_logs.unlink()
        return count

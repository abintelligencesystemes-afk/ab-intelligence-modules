# -*- coding: utf-8 -*-
"""Pilier 6 — Dashboard DPO.

TransientModel exposant les KPIs de conformité au DPO.
"""
from datetime import timedelta
from odoo import api, fields, models


class AbrmdRgpdDashboard(models.TransientModel):
    _name = "abrmd.rgpd.dashboard"
    _description = "Dashboard DPO RGPD"

    # KPI Pilier 1 — Registre Art.30
    registre_count = fields.Integer(string="Traitements actifs", compute="_compute_kpis")
    registre_sensitive_count = fields.Integer(string="Traitements de données sensibles", compute="_compute_kpis")

    # KPI Pilier 2 — Consentements
    consent_active_count = fields.Integer(string="Consentements actifs", compute="_compute_kpis")
    consent_withdrawn_count = fields.Integer(string="Consentements retirés (30j)", compute="_compute_kpis")
    consent_expired_count = fields.Integer(string="Consentements expirés (30j)", compute="_compute_kpis")

    # KPI Pilier 3 — Demandes
    request_open_count = fields.Integer(string="Demandes en cours", compute="_compute_kpis")
    request_overdue_count = fields.Integer(string="Demandes en retard ⚠", compute="_compute_kpis")
    request_at_risk_count = fields.Integer(string="Demandes échéance < 7j", compute="_compute_kpis")
    request_done_30d = fields.Integer(string="Demandes traitées (30j)", compute="_compute_kpis")

    # KPI Pilier 5 — Logs
    access_logs_24h = fields.Integer(string="Accès données (24h)", compute="_compute_kpis")
    access_logs_sensitive_24h = fields.Integer(string="Accès données sensibles (24h)", compute="_compute_kpis")

    # Alertes
    alerts_html = fields.Html(string="Alertes", compute="_compute_kpis", sanitize=False)

    # Contact DPO
    dpo_name = fields.Char(string="DPO", compute="_compute_kpis")
    dpo_email = fields.Char(string="Email DPO", compute="_compute_kpis")

    @api.depends_context("uid")
    def _compute_kpis(self):
        now = fields.Datetime.now()
        d30 = now - timedelta(days=30)
        d1 = now - timedelta(hours=24)
        d7 = now + timedelta(days=7)

        registre = self.env["abrmd.rgpd.registre"].sudo()
        consent = self.env["abrmd.rgpd.consent"].sudo()
        request = self.env["abrmd.rgpd.request"].sudo()
        log = self.env["abrmd.rgpd.access.log"].sudo()
        params = self.env["ir.config_parameter"].sudo()

        for rec in self:
            rec.registre_count = registre.search_count([("active", "=", True)])
            rec.registre_sensitive_count = registre.search_count([
                ("active", "=", True), ("data_sensitive", "=", True),
            ])

            rec.consent_active_count = consent.search_count([("state", "=", "given")])
            rec.consent_withdrawn_count = consent.search_count([
                ("state", "=", "withdrawn"),
                ("withdrawal_date", ">=", d30),
            ])
            rec.consent_expired_count = consent.search_count([
                ("state", "=", "expired"),
                ("write_date", ">=", d30),
            ])

            rec.request_open_count = request.search_count([
                ("state", "in", ("received", "identity_check", "in_progress", "extended")),
            ])
            rec.request_overdue_count = request.search_count([("is_overdue", "=", True)])
            rec.request_at_risk_count = request.search_count([
                ("state", "in", ("received", "identity_check", "in_progress", "extended")),
                ("deadline_date", "<=", d7),
                ("deadline_date", ">=", now),
            ])
            rec.request_done_30d = request.search_count([
                ("state", "in", ("done", "refused")),
                ("closed_date", ">=", d30),
            ])

            rec.access_logs_24h = log.search_count([("create_date", ">=", d1)])
            rec.access_logs_sensitive_24h = log.search_count([
                ("create_date", ">=", d1), ("sensitive", "=", True),
            ])

            rec.dpo_name = params.get_param("abrmd_ai_rgpd.dpo_name", "Non défini")
            rec.dpo_email = params.get_param("abrmd_ai_rgpd.dpo_email", "")

            # Compose alerts
            alerts = []
            if rec.request_overdue_count:
                alerts.append(
                    "<div class='alert alert-danger'>🚨 %d demande(s) RGPD en retard légal — réponse hors délai d'1 mois.</div>"
                    % rec.request_overdue_count
                )
            if rec.request_at_risk_count:
                alerts.append(
                    "<div class='alert alert-warning'>⚠ %d demande(s) RGPD à échéance dans les 7 jours.</div>"
                    % rec.request_at_risk_count
                )
            if not rec.dpo_email:
                alerts.append(
                    "<div class='alert alert-info'>ℹ Le contact DPO n'est pas configuré (Paramètres → AI RGPD).</div>"
                )
            if rec.registre_count == 0:
                alerts.append(
                    "<div class='alert alert-warning'>⚠ Le registre Article 30 est vide. Renseigne au moins les traitements principaux.</div>"
                )
            rec.alerts_html = "".join(alerts) or "<div class='alert alert-success'>✓ Aucune alerte RGPD critique.</div>"

    @api.model
    def action_open_dashboard(self):
        """Action pour ouvrir le dashboard en mode form."""
        rec = self.create({})
        return {
            "name": "Dashboard DPO",
            "type": "ir.actions.act_window",
            "res_model": "abrmd.rgpd.dashboard",
            "view_mode": "form",
            "res_id": rec.id,
            "target": "current",
        }

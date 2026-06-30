# -*- coding: utf-8 -*-
"""Pilier 3 — Demandes d'exercice des droits (Art.12-22 RGPD).

Délai légal : 1 mois (Art.12.3), prolongeable de 2 mois supplémentaires
si complexité justifiée. L'information doit être fournie gratuitement (Art.12.5)
sauf demande manifestement infondée ou excessive.
"""
from datetime import timedelta
from odoo import api, fields, models
from odoo.exceptions import UserError


REQUEST_TYPE_LABELS = {
    "access": "Droit d'accès (Art.15)",
    "rectification": "Droit de rectification (Art.16)",
    "erasure": "Droit à l'effacement (Art.17)",
    "restriction": "Limitation du traitement (Art.18)",
    "portability": "Droit à la portabilité (Art.20)",
    "objection": "Droit d'opposition (Art.21)",
    "automated_decision": "Décision individuelle automatisée (Art.22)",
}


class AbrmdRgpdRequest(models.Model):
    _name = "abrmd.rgpd.request"
    _description = "Demande d'exercice des droits RGPD"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "received_date desc, id desc"

    name = fields.Char(string="Référence", default=lambda s: "Nouvelle demande", required=True)

    # Type de demande
    request_type = fields.Selection(
        [
            ("access", "Droit d'accès (Art.15)"),
            ("rectification", "Droit de rectification (Art.16)"),
            ("erasure", "Droit à l'effacement / oubli (Art.17)"),
            ("restriction", "Limitation du traitement (Art.18)"),
            ("portability", "Droit à la portabilité (Art.20)"),
            ("objection", "Droit d'opposition (Art.21)"),
            ("automated_decision", "Décision individuelle automatisée (Art.22)"),
        ],
        string="Type de demande",
        required=True,
        tracking=True,
    )

    # Sujet de la demande
    partner_id = fields.Many2one("res.partner", string="Personne concernée", ondelete="restrict")
    subject_name = fields.Char(string="Nom du demandeur", required=True)
    subject_email = fields.Char(string="Email du demandeur", required=True)
    subject_phone = fields.Char(string="Téléphone du demandeur")

    # Workflow
    state = fields.Selection(
        [
            ("draft", "Brouillon"),
            ("received", "Reçue"),
            ("identity_check", "Vérification d'identité"),
            ("in_progress", "En cours de traitement"),
            ("extended", "Délai prolongé (Art.12.3)"),
            ("done", "Réponse envoyée"),
            ("refused", "Refusée"),
        ],
        string="État",
        default="draft",
        required=True,
        tracking=True,
    )

    # Dates et délais
    received_date = fields.Datetime(
        string="Date de réception",
        default=fields.Datetime.now,
        required=True,
        tracking=True,
    )
    deadline_date = fields.Datetime(
        string="Échéance légale",
        compute="_compute_deadline_date",
        store=True,
        help="Date limite de réponse (1 mois, prolongeable de 2 mois).",
    )
    closed_date = fields.Datetime(string="Date de clôture", tracking=True)
    extension_reason = fields.Text(
        string="Motif de prolongation",
        help="À documenter si délai prolongé au-delà du mois légal (Art.12.3).",
    )

    # Demande
    description = fields.Html(string="Détail de la demande")
    identity_verified = fields.Boolean(
        string="Identité vérifiée",
        tracking=True,
        help="Pré-requis avant tout traitement (Art.12.6).",
    )
    identity_verification_method = fields.Char(
        string="Méthode de vérification",
        help="Ex: copie pièce d'identité reçue par email, vérification appel téléphonique, etc.",
    )

    # Réponse
    response = fields.Html(string="Réponse au demandeur")
    response_attachment_ids = fields.Many2many(
        "ir.attachment",
        string="Pièces jointes de la réponse",
        help="Documents fournis au sujet (export des données, copie corrigée, etc.).",
    )
    refusal_reason = fields.Text(
        string="Motif de refus",
        help="Si la demande est manifestement infondée ou excessive (Art.12.5).",
    )

    # Métadonnées
    days_to_deadline = fields.Integer(
        string="Jours restants",
        compute="_compute_days_to_deadline",
        help="Nombre de jours avant l'échéance légale.",
    )
    is_overdue = fields.Boolean(
        string="En retard",
        compute="_compute_days_to_deadline",
        store=True,
    )

    @api.depends("received_date")
    def _compute_deadline_date(self):
        params = self.env["ir.config_parameter"].sudo()
        days = int(params.get_param("abrmd_ai_rgpd.request_default_deadline_days", 30))
        for rec in self:
            if rec.received_date:
                rec.deadline_date = rec.received_date + timedelta(days=days)
            else:
                rec.deadline_date = False

    @api.depends("deadline_date", "state")
    def _compute_days_to_deadline(self):
        now = fields.Datetime.now()
        for rec in self:
            if rec.deadline_date and rec.state not in ("done", "refused"):
                delta = rec.deadline_date - now
                rec.days_to_deadline = delta.days
                rec.is_overdue = delta.days < 0
            else:
                rec.days_to_deadline = 0
                rec.is_overdue = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "Nouvelle demande") == "Nouvelle demande":
                seq = self.env["ir.sequence"].next_by_code("abrmd.rgpd.request") or "RGPD-REQ"
                vals["name"] = seq
        return super().create(vals_list)

    # ---- Workflow actions ----
    def action_mark_received(self):
        for rec in self:
            rec.write({"state": "received"})
            # Activité auto pour vérifier l'identité dans les 3 jours
            rec.activity_schedule(
                "mail.mail_activity_data_todo",
                summary="Vérifier l'identité du demandeur (Art.12.6)",
                date_deadline=fields.Date.today() + timedelta(days=3),
                user_id=rec.env.user.id,
            )
        return True

    def action_identity_verified(self):
        for rec in self:
            if not rec.identity_verification_method:
                raise UserError(
                    "Renseigne la méthode de vérification d'identité avant de valider."
                )
            rec.write({"identity_verified": True, "state": "in_progress"})
            rec.message_post(
                body="Identité vérifiée : %s" % rec.identity_verification_method,
                subtype_xmlid="mail.mt_note",
            )
        return True

    def action_extend_deadline(self):
        for rec in self:
            if not rec.extension_reason:
                raise UserError(
                    "Le motif de prolongation est obligatoire (Art.12.3). "
                    "Il doit être notifié au sujet dans le mois initial."
                )
            rec.write({
                "state": "extended",
                "deadline_date": rec.deadline_date + timedelta(days=60),
            })
            rec.message_post(
                body="Délai prolongé de 2 mois. Motif : %s" % rec.extension_reason,
                subtype_xmlid="mail.mt_note",
            )
        return True

    def action_close_done(self):
        for rec in self:
            if not rec.response:
                raise UserError("La réponse au demandeur est obligatoire avant clôture.")
            rec.write({
                "state": "done",
                "closed_date": fields.Datetime.now(),
            })
        return True

    def action_close_refused(self):
        for rec in self:
            if not rec.refusal_reason:
                raise UserError(
                    "Le motif de refus est obligatoire (Art.12.5). "
                    "Il doit être communiqué au sujet ainsi que les voies de recours."
                )
            rec.write({
                "state": "refused",
                "closed_date": fields.Datetime.now(),
            })
        return True

    @api.model
    def _cron_alert_deadlines(self):
        """Cron quotidien — alerte mail.activity sur les demandes à échéance < 7 jours."""
        threshold = fields.Datetime.now() + timedelta(days=7)
        at_risk = self.search([
            ("state", "in", ("received", "identity_check", "in_progress", "extended")),
            ("deadline_date", "<=", threshold),
        ])
        for rec in at_risk:
            # Crée une activité seulement si pas déjà programmée
            existing = rec.activity_ids.filtered(lambda a: "RGPD" in (a.summary or ""))
            if not existing:
                rec.activity_schedule(
                    "mail.mail_activity_data_todo",
                    summary="⚠ RGPD — Demande à échéance < 7 jours",
                    note="La demande %s arrive à échéance légale le %s." % (
                        rec.name, rec.deadline_date,
                    ),
                    date_deadline=fields.Date.today(),
                    user_id=rec.env.user.id,
                )
        return len(at_risk)

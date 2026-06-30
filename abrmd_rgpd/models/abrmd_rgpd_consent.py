# -*- coding: utf-8 -*-
"""Pilier 2 — Consentements (Art.7 RGPD).

Capture du consentement, retrait, historique horodaté.
Le consentement doit être libre, spécifique, éclairé et univoque.
Il doit pouvoir être retiré aussi facilement qu'il a été donné.
"""
import hashlib
from datetime import datetime
from odoo import api, fields, models


class AbrmdRgpdConsent(models.Model):
    _name = "abrmd.rgpd.consent"
    _description = "Consentement RGPD"
    _inherit = ["mail.thread"]
    _order = "consent_date desc, id desc"

    name = fields.Char(
        string="Référence",
        compute="_compute_name",
        store=True,
        index=True,
    )

    # Sujet (personne concernée)
    partner_id = fields.Many2one("res.partner", string="Personne concernée", ondelete="restrict")
    subject_email = fields.Char(
        string="Email du sujet",
        required=True,
        help="Email de la personne concernée (peut être différent du partner si externe).",
    )
    subject_hash = fields.Char(
        string="Hash du sujet (SHA-256)",
        compute="_compute_subject_hash",
        store=True,
        help="Hash SHA-256 + sel de l'email — utilisé en pseudonymisation pour le DPO Dashboard.",
    )

    # Traitement concerné
    registre_id = fields.Many2one(
        "abrmd.rgpd.registre", string="Traitement", required=True, ondelete="restrict"
    )
    purpose = fields.Char(
        string="Finalité spécifique",
        required=True,
        help="Si plusieurs finalités existent dans le traitement, préciser laquelle.",
    )

    # État du consentement
    state = fields.Selection(
        [
            ("given", "Donné"),
            ("withdrawn", "Retiré"),
            ("expired", "Expiré"),
        ],
        string="État",
        default="given",
        required=True,
        tracking=True,
    )
    consent_date = fields.Datetime(
        string="Date de capture",
        default=fields.Datetime.now,
        required=True,
        tracking=True,
    )
    withdrawal_date = fields.Datetime(
        string="Date de retrait",
        tracking=True,
    )
    expiry_date = fields.Datetime(
        string="Date d'expiration",
        help="Optionnel — utile pour les consentements à durée limitée (ex: 2 ans).",
    )

    # Mode de capture
    capture_method = fields.Selection(
        [
            ("web_form", "Formulaire web"),
            ("email_optin", "Email opt-in (double opt-in)"),
            ("paper", "Formulaire papier"),
            ("verbal", "Verbal (à éviter)"),
            ("imported", "Import migration"),
            ("api", "API"),
            ("other", "Autre"),
        ],
        string="Mode de capture",
        required=True,
        default="web_form",
    )

    # Trace de preuve
    proof_url = fields.Char(string="URL de la preuve", help="Ex: lien vers le formulaire signé.")
    proof_ip = fields.Char(
        string="IP source",
        help="IP de la personne lors du clic — anonymisée /24 pour IPv4, /48 pour IPv6.",
    )
    proof_user_agent = fields.Char(string="User Agent")
    notice_version = fields.Char(
        string="Version de la notice affichée",
        help="Référence à la version du document d'information affiché au moment du consentement.",
    )

    notes = fields.Text(string="Notes")

    @api.depends("partner_id", "subject_email", "purpose", "consent_date")
    def _compute_name(self):
        for rec in self:
            base = rec.subject_email or (rec.partner_id and rec.partner_id.name) or "Anonyme"
            date_str = rec.consent_date and rec.consent_date.strftime("%Y-%m-%d") or "?"
            rec.name = "%s · %s · %s" % (base, rec.purpose or "?", date_str)

    @api.depends("subject_email")
    def _compute_subject_hash(self):
        params = self.env["ir.config_parameter"].sudo()
        salt = params.get_param("abrmd_ai_rgpd.anonymization_salt", "default-salt-change-me")
        for rec in self:
            if rec.subject_email:
                value = (rec.subject_email.lower().strip() + "|" + salt).encode("utf-8")
                rec.subject_hash = hashlib.sha256(value).hexdigest()
            else:
                rec.subject_hash = False

    def action_withdraw(self):
        """Retrait du consentement (Art.7.3) — aussi facile que la capture."""
        for rec in self:
            rec.write({
                "state": "withdrawn",
                "withdrawal_date": fields.Datetime.now(),
            })
            rec.message_post(
                body="Consentement retiré (Art.7.3 RGPD).",
                subtype_xmlid="mail.mt_note",
            )
        return True

    def action_renew(self):
        """Renouvellement d'un consentement expiré ou retiré — crée une nouvelle entrée."""
        new_records = self.env["abrmd.rgpd.consent"]
        for rec in self:
            new = rec.copy({
                "state": "given",
                "consent_date": fields.Datetime.now(),
                "withdrawal_date": False,
            })
            new_records |= new
        return {
            "name": "Consentement renouvelé",
            "type": "ir.actions.act_window",
            "res_model": "abrmd.rgpd.consent",
            "view_mode": "form",
            "res_id": new_records[:1].id,
        }

    @api.model
    def _cron_check_expired(self):
        """Cron quotidien — bascule les consentements expirés."""
        expired = self.search([
            ("state", "=", "given"),
            ("expiry_date", "!=", False),
            ("expiry_date", "<=", fields.Datetime.now()),
        ])
        for rec in expired:
            rec.write({"state": "expired"})
            rec.message_post(body="Consentement expiré automatiquement (date dépassée).")
        return len(expired)

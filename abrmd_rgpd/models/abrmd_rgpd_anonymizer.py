# -*- coding: utf-8 -*-
"""Pilier 4 — Anonymisation et pseudonymisation (Art.4.5 + Art.17 + Art.32 RGPD).

L'anonymisation rend la personne non identifiable (pas de retour possible).
La pseudonymisation conserve un lien indirect (clé) qui permet la ré-identification.

Ce service expose des Server Actions et un AbstractModel utilitaire.
"""
import hashlib
import re
from odoo import api, fields, models
from odoo.exceptions import UserError


class AbrmdRgpdAnonymizer(models.AbstractModel):
    _name = "abrmd.rgpd.anonymizer"
    _description = "Service d'anonymisation / pseudonymisation RGPD"

    # ---- API publique ----
    @api.model
    def get_salt(self):
        params = self.env["ir.config_parameter"].sudo()
        salt = params.get_param("abrmd_ai_rgpd.anonymization_salt", "")
        if not salt:
            # Génère un sel cryptographique stable côté tenant
            import secrets
            salt = secrets.token_hex(32)
            params.set_param("abrmd_ai_rgpd.anonymization_salt", salt)
        return salt

    @api.model
    def pseudonymize(self, value):
        """Pseudonymise une valeur : sortie = SHA-256(value + sel)."""
        if not value:
            return ""
        salt = self.get_salt()
        payload = (str(value).lower().strip() + "|" + salt).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    @api.model
    def anonymize_email(self, email):
        """Anonymise un email : 'a***@example.com'."""
        if not email or "@" not in email:
            return ""
        local, domain = email.split("@", 1)
        if len(local) <= 1:
            return "*@" + domain
        return local[0] + "***@" + domain

    @api.model
    def anonymize_phone(self, phone):
        """Anonymise un téléphone : conserve les 2 premiers et 2 derniers chiffres."""
        if not phone:
            return ""
        digits = re.sub(r"\D", "", phone)
        if len(digits) < 6:
            return "***"
        return digits[:2] + "*" * (len(digits) - 4) + digits[-2:]

    @api.model
    def anonymize_ip(self, ip):
        """Anonymise une IP : v4 -> /24, v6 -> /48."""
        if not ip:
            return ""
        if ":" in ip:
            # IPv6 -> /48
            parts = ip.split(":")
            return ":".join(parts[:3]) + "::/48"
        # IPv4 -> /24
        parts = ip.split(".")
        if len(parts) == 4:
            return ".".join(parts[:3]) + ".0/24"
        return ip

    @api.model
    def anonymize_partner(self, partner, mode="pseudonymize", keep_aggregates=True):
        """Anonymise un res.partner.

        :param partner: enregistrement res.partner
        :param mode: 'pseudonymize' (réversible via clé) ou 'anonymize' (irréversible)
        :param keep_aggregates: si True, conserve les compteurs d'agrégation
                                  (utile pour reporting agrégé post-effacement).
        :return: dict avec champs modifiés
        """
        if not partner:
            return {}

        if mode == "anonymize":
            vals = {
                "name": "Anonymisé · %s" % partner.id,
                "email": False,
                "phone": False,
                "mobile": False,
                "street": False,
                "street2": False,
                "city": False,
                "zip": False,
                "vat": False,
                "comment": False,
            }
        else:  # pseudonymize
            vals = {
                "name": "Pseudo · %s" % self.pseudonymize(partner.email or partner.name or partner.id)[:16],
                "email": self.pseudonymize(partner.email) + "@pseudo.local" if partner.email else False,
                "phone": False,
                "mobile": False,
                "comment": "[Pseudonymisé le %s]" % fields.Datetime.now(),
            }

        partner.sudo().write(vals)

        # Trace dans le log d'accès
        self.env["abrmd.rgpd.access.log"].sudo().create({
            "log_type": "anonymization",
            "model_id": self.env["ir.model"].search([("model", "=", "res.partner")], limit=1).id,
            "res_id": partner.id,
            "subject_hash": self.pseudonymize("res.partner:%s" % partner.id),
            "action_description": "Anonymisation %s (mode=%s)" % (partner.id, mode),
            "executed_by": self.env.user.id,
        })

        return vals

    # ---- Actions Server (appelables depuis l'UI) ----
    @api.model
    def server_action_pseudonymize_partner(self):
        """À utiliser depuis une action serveur sur res.partner."""
        active_ids = self.env.context.get("active_ids") or self.env.context.get("active_id")
        if not active_ids:
            raise UserError("Aucun partenaire sélectionné.")
        if isinstance(active_ids, int):
            active_ids = [active_ids]
        partners = self.env["res.partner"].browse(active_ids)
        for p in partners:
            self.anonymize_partner(p, mode="pseudonymize")
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "RGPD",
                "message": "%d partenaire(s) pseudonymisé(s)." % len(partners),
                "type": "success",
                "sticky": False,
            },
        }

    @api.model
    def server_action_anonymize_partner(self):
        """À utiliser depuis une action serveur sur res.partner (IRRÉVERSIBLE)."""
        active_ids = self.env.context.get("active_ids") or self.env.context.get("active_id")
        if not active_ids:
            raise UserError("Aucun partenaire sélectionné.")
        if isinstance(active_ids, int):
            active_ids = [active_ids]
        partners = self.env["res.partner"].browse(active_ids)
        for p in partners:
            self.anonymize_partner(p, mode="anonymize")
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "RGPD — Anonymisation effectuée",
                "message": "%d partenaire(s) anonymisé(s) DÉFINITIVEMENT (Art.17)." % len(partners),
                "type": "warning",
                "sticky": True,
            },
        }

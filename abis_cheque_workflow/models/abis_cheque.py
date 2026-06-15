# -*- coding: utf-8 -*-
"""Modèle métier abis.cheque — un chèque bancaire avec son workflow."""
from odoo import _, api, fields, models
from odoo.exceptions import UserError


CHEQUE_STATES = [
    ("draft", "Brouillon"),
    ("emitted", "Émis"),
    ("in_bank", "En banque (déposé)"),
    ("cashed", "Encaissé"),
    ("rejected", "Rejeté"),
    ("cancelled", "Annulé"),
]


class AbisCheque(models.Model):
    _name = "abis.cheque"
    _description = "Chèque bancaire — émis ou reçu"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "issue_date desc, name"

    name = fields.Char(
        string="Référence interne",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("Nouveau"),
    )
    direction = fields.Selection(
        [("inbound", "Reçu (client)"), ("outbound", "Émis (fournisseur)")],
        string="Sens",
        required=True,
        default="inbound",
        tracking=True,
    )
    cheque_number = fields.Char(
        string="Numéro de chèque",
        required=True,
        tracking=True,
        help="Numéro figurant en bas du chèque.",
    )
    bank_name = fields.Char(string="Banque émettrice", required=True, tracking=True)
    bank_account = fields.Char(string="Compte / RIB partiel")
    drawer_name = fields.Char(
        string="Titulaire du chèque",
        required=True,
        help="Nom de la personne / société qui a signé le chèque.",
    )
    partner_id = fields.Many2one(
        "res.partner", string="Partenaire", required=True, tracking=True
    )
    issue_date = fields.Date(
        string="Date d'émission", required=True, default=fields.Date.context_today, tracking=True
    )
    amount = fields.Monetary(string="Montant", required=True, tracking=True)
    currency_id = fields.Many2one(
        "res.currency",
        string="Devise",
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    state = fields.Selection(
        CHEQUE_STATES,
        string="Statut",
        default="draft",
        tracking=True,
        copy=False,
        required=True,
    )

    # Workflow timestamps
    emitted_date = fields.Date(string="Date d'émission saisie")
    deposit_date = fields.Date(string="Date de dépôt en banque", tracking=True)
    cashed_date = fields.Date(string="Date d'encaissement", tracking=True)
    rejected_date = fields.Date(string="Date de rejet", tracking=True)
    rejection_reason = fields.Selection(
        [
            ("insufficient_funds", "Provision insuffisante"),
            ("invalid_signature", "Signature invalide"),
            ("stop_payment", "Opposition"),
            ("closed_account", "Compte clos"),
            ("other", "Autre"),
        ],
        string="Motif rejet",
        tracking=True,
    )

    # Liens métier
    invoice_id = fields.Many2one(
        "account.move",
        string="Facture liée",
        domain="[('move_type', 'in', ('out_invoice','in_invoice'))]",
    )
    sale_order_id = fields.Many2one("sale.order", string="Commande liée")
    remise_id = fields.Many2one(
        "abis.cheque.remise",
        string="Bordereau de remise",
        ondelete="set null",
        tracking=True,
    )
    payment_id = fields.Many2one(
        "account.payment",
        string="Paiement Odoo",
        copy=False,
        ondelete="set null",
    )
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company
    )

    # ====== ORM ======
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("Nouveau")) == _("Nouveau"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "abis.cheque"
                ) or _("Nouveau")
        return super().create(vals_list)

    # ====== Workflow actions ======
    def action_emit(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("Seuls les chèques en brouillon peuvent être émis."))
            rec.write({"state": "emitted", "emitted_date": fields.Date.today()})

    def action_deposit(self):
        """À utiliser depuis un bordereau de remise."""
        for rec in self:
            if rec.state != "emitted":
                raise UserError(
                    _("Le chèque '%s' doit être en statut 'Émis' pour être déposé.")
                    % rec.name
                )
            rec.write(
                {"state": "in_bank", "deposit_date": fields.Date.today()}
            )

    def action_cash(self):
        for rec in self:
            if rec.state != "in_bank":
                raise UserError(
                    _("Le chèque '%s' doit être en banque pour être encaissé.")
                    % rec.name
                )
            rec.write(
                {"state": "cashed", "cashed_date": fields.Date.today()}
            )

    def action_reject(self):
        for rec in self:
            if rec.state not in ("emitted", "in_bank"):
                raise UserError(
                    _("Le chèque '%s' ne peut être rejeté dans ce statut.")
                    % rec.name
                )
            rec.write(
                {"state": "rejected", "rejected_date": fields.Date.today()}
            )
            # Déclenche template mail de relance
            template = self.env.ref(
                "abis_cheque_workflow.mail_template_cheque_rejected",
                raise_if_not_found=False,
            )
            if template and rec.partner_id.email:
                template.send_mail(rec.id, force_send=False)

    def action_cancel(self):
        for rec in self:
            if rec.state == "cashed":
                raise UserError(_("Un chèque encaissé ne peut être annulé."))
            rec.state = "cancelled"

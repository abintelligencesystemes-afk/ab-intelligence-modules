# -*- coding: utf-8 -*-
"""Bordereau de remise en banque groupée de plusieurs chèques."""
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AbisChequeRemise(models.Model):
    _name = "abis.cheque.remise"
    _description = "Bordereau de remise en banque"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "deposit_date desc, name"

    name = fields.Char(
        string="N° bordereau",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("Nouveau"),
    )
    deposit_date = fields.Date(
        string="Date de remise",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    bank_journal_id = fields.Many2one(
        "account.journal",
        string="Journal banque",
        required=True,
        domain="[('type', '=', 'bank')]",
        tracking=True,
    )
    cheque_ids = fields.One2many(
        "abis.cheque", "remise_id", string="Chèques inclus"
    )
    cheque_count = fields.Integer(
        compute="_compute_totals", string="Nb chèques"
    )
    total_amount = fields.Monetary(
        compute="_compute_totals", string="Total bordereau", store=True
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="bank_journal_id.currency_id",
        string="Devise",
        store=True,
    )
    state = fields.Selection(
        [
            ("draft", "Brouillon"),
            ("deposited", "Remis"),
            ("cashed", "Encaissé"),
        ],
        string="Statut",
        default="draft",
        tracking=True,
        required=True,
    )
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company
    )

    @api.depends("cheque_ids", "cheque_ids.amount")
    def _compute_totals(self):
        for rec in self:
            rec.cheque_count = len(rec.cheque_ids)
            rec.total_amount = sum(rec.cheque_ids.mapped("amount"))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("Nouveau")) == _("Nouveau"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "abis.cheque.remise"
                ) or _("Nouveau")
        return super().create(vals_list)

    def action_deposit(self):
        for rec in self:
            if not rec.cheque_ids:
                raise UserError(_("Bordereau vide : ajoute au moins 1 chèque."))
            rec.cheque_ids.action_deposit()
            rec.state = "deposited"

    def action_cash_all(self):
        for rec in self:
            rec.cheque_ids.filtered(lambda c: c.state == "in_bank").action_cash()
            rec.state = "cashed"

    def action_print_report(self):
        return self.env.ref(
            "abis_cheque_workflow.action_cheque_remise_report"
        ).report_action(self)

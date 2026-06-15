# -*- coding: utf-8 -*-
"""Wizard d'émission d'un chèque depuis une facture / commande."""
from odoo import _, api, fields, models


class AbisChequeEmitWizard(models.TransientModel):
    _name = "abis.cheque.emit.wizard"
    _description = "Émission d'un chèque depuis facture / commande"

    invoice_id = fields.Many2one("account.move", string="Facture")
    sale_order_id = fields.Many2one("sale.order", string="Commande")
    partner_id = fields.Many2one(
        "res.partner", string="Partenaire", required=True
    )
    cheque_number = fields.Char(string="N° chèque", required=True)
    bank_name = fields.Char(string="Banque", required=True)
    drawer_name = fields.Char(string="Titulaire", required=True)
    amount = fields.Monetary(string="Montant", required=True)
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id,
    )
    issue_date = fields.Date(
        string="Date d'émission",
        required=True,
        default=fields.Date.context_today,
    )

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        active_model = self.env.context.get("active_model")
        active_id = self.env.context.get("active_id")
        if active_model == "account.move" and active_id:
            inv = self.env["account.move"].browse(active_id)
            defaults.update(
                {
                    "invoice_id": inv.id,
                    "partner_id": inv.partner_id.id,
                    "amount": inv.amount_residual,
                    "drawer_name": inv.partner_id.name,
                }
            )
        elif active_model == "sale.order" and active_id:
            so = self.env["sale.order"].browse(active_id)
            defaults.update(
                {
                    "sale_order_id": so.id,
                    "partner_id": so.partner_id.id,
                    "amount": so.amount_total,
                    "drawer_name": so.partner_id.name,
                }
            )
        return defaults

    def action_create_cheque(self):
        self.ensure_one()
        cheque = self.env["abis.cheque"].create(
            {
                "direction": "inbound",
                "cheque_number": self.cheque_number,
                "bank_name": self.bank_name,
                "drawer_name": self.drawer_name,
                "partner_id": self.partner_id.id,
                "issue_date": self.issue_date,
                "amount": self.amount,
                "currency_id": self.currency_id.id,
                "invoice_id": self.invoice_id.id if self.invoice_id else False,
                "sale_order_id": self.sale_order_id.id if self.sale_order_id else False,
                "state": "emitted",
                "emitted_date": fields.Date.today(),
            }
        )
        return {
            "name": _("Chèque émis"),
            "type": "ir.actions.act_window",
            "res_model": "abis.cheque",
            "res_id": cheque.id,
            "view_mode": "form",
        }

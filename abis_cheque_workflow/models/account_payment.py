# -*- coding: utf-8 -*-
"""Lien faible entre account.payment et abis.cheque."""
from odoo import fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    abis_cheque_id = fields.Many2one(
        "abis.cheque",
        string="Chèque ABIS",
        ondelete="set null",
        help="Chèque ABIS associé à ce paiement.",
    )

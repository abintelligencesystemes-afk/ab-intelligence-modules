# -*- coding: utf-8 -*-
"""Remise globale TTC sur account.move (factures clients)."""
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    abis_discount_ttc_mode = fields.Selection(
        [
            ("none", "Aucune"),
            ("amount", "Montant € TTC"),
            ("percent", "Pourcentage %"),
        ],
        string="Type de remise globale TTC",
        default="none",
    )
    abis_discount_ttc_amount = fields.Monetary(string="Remise TTC (€)")
    abis_discount_ttc_percent = fields.Float(string="Remise TTC (%)")
    abis_discount_applied = fields.Boolean(
        string="Remise globale TTC appliquée", readonly=True, copy=False
    )

    def action_apply_abis_discount_ttc(self):
        for move in self:
            if move.state != "draft":
                raise UserError(_("La facture doit être en brouillon."))
            if move.abis_discount_ttc_mode == "none":
                raise UserError(_("Aucune remise globale TTC à appliquer."))
            if move.abis_discount_applied:
                raise UserError(_("Remise déjà appliquée."))

            total_ttc = move.amount_total
            if not total_ttc:
                raise UserError(_("Total TTC nul, impossible de calculer."))

            if move.abis_discount_ttc_mode == "amount":
                discount_ttc = move.abis_discount_ttc_amount
            else:
                discount_ttc = total_ttc * (move.abis_discount_ttc_percent or 0.0) / 100.0

            if discount_ttc <= 0 or discount_ttc >= total_ttc:
                raise UserError(_("Remise invalide."))

            ratio = (total_ttc - discount_ttc) / total_ttc
            for line in move.invoice_line_ids:
                line.price_unit = round(line.price_unit * ratio, 4)
            move.abis_discount_applied = True

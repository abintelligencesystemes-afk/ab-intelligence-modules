# -*- coding: utf-8 -*-
"""Remise globale TTC sur sale.order — répartition prorata multi-TVA."""
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    abis_discount_ttc_mode = fields.Selection(
        [
            ("none", "Aucune"),
            ("amount", "Montant € TTC"),
            ("percent", "Pourcentage %"),
        ],
        string="Type de remise globale TTC",
        default="none",
    )
    abis_discount_ttc_amount = fields.Monetary(
        string="Remise TTC (€)",
        help="Montant total de la remise globale TTC en euros.",
    )
    abis_discount_ttc_percent = fields.Float(
        string="Remise TTC (%)",
        help="Pourcentage de remise globale TTC (0-100).",
    )
    abis_discount_applied = fields.Boolean(
        string="Remise globale TTC appliquée",
        readonly=True,
        copy=False,
        help="Cocher cette case signifie que la remise a été propagée sur "
             "les lignes au prorata. Décocher remet les lignes à leur prix initial.",
    )

    def action_apply_abis_discount_ttc(self):
        """Répartit la remise globale TTC au prorata des lignes."""
        for order in self:
            if order.abis_discount_ttc_mode == "none":
                raise UserError(_("Aucune remise globale TTC à appliquer."))
            if order.abis_discount_applied:
                raise UserError(
                    _("La remise est déjà appliquée. Annule-la d'abord pour la recalculer.")
                )

            # Réf : total TTC actuel avant remise
            total_ttc = order.amount_total
            if not total_ttc:
                raise UserError(_("Le total TTC est nul, impossible de calculer la remise."))

            # Calcul du montant TTC de remise
            if order.abis_discount_ttc_mode == "amount":
                discount_ttc = order.abis_discount_ttc_amount
            else:
                discount_ttc = total_ttc * (order.abis_discount_ttc_percent or 0.0) / 100.0

            if discount_ttc <= 0:
                raise UserError(_("La remise doit être strictement positive."))
            if discount_ttc >= total_ttc:
                raise UserError(_("La remise doit rester inférieure au total TTC."))

            # Ratio de réduction
            ratio = (total_ttc - discount_ttc) / total_ttc

            # Application sur chaque ligne via price_unit * ratio
            # Garder trace des prix initiaux pour pouvoir annuler
            for line in order.order_line:
                line.price_unit = round(line.price_unit * ratio, 4)
            order.abis_discount_applied = True

    def action_cancel_abis_discount_ttc(self):
        """Recalcule les prix lignes (impossible sans snapshot) — on bascule
        juste le flag pour autoriser l'utilisateur à corriger manuellement."""
        for order in self:
            order.abis_discount_applied = False
        return {
            "warning": {
                "title": _("Remise annulée"),
                "message": _(
                    "Le flag a été décoché. Les prix unitaires des lignes "
                    "ont été modifiés lors de l'application — pense à les "
                    "remettre manuellement si besoin."
                ),
            }
        }

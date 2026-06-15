# abis_cheque_workflow — Workflow chèques bancaires

Gère le cycle complet d'un chèque bancaire dans Odoo : émission, dépôt en
banque, encaissement, rejet, relance.

## Fonctionnalités

- Modèle `abis.cheque` avec workflow draft → emitted → in_bank → cashed/rejected
- Wizard d'émission depuis facture (`account.move`) ou commande (`sale.order`)
- Bordereau de remise en banque groupé (`abis.cheque.remise`)
- PDF de bordereau prêt à imprimer
- Relance email automatique sur rejet
- Lien vers `account.payment` standard Odoo

## Installation

1. Apps → cherche "ABIS Cheque Workflow"
2. Installe
3. Menu Comptabilité → Chèques bancaires

## Tarification

149.00 € (achat unique OPL-1).

## Auteur

AB Intelligence Systèmes — Anthony Boursier

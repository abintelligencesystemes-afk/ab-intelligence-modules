# -*- coding: utf-8 -*-
{
    "name": "ABIS Sale TTC — Remise globale TTC",
    "summary": "Applique une remise globale TTC en € ou % sur les commandes "
               "et factures. Recalcule automatiquement les lignes au prorata.",
    "description": """
ABIS Sale TTC — Remise globale TTC
===================================

Vos commerciaux négocient un prix final TTC ("550 € tout compris") mais
Odoo ne sait que gérer des remises HT par ligne. Résultat : recalcul manuel
fastidieux et risque d'erreur.

ABIS Sale TTC ajoute deux champs sur sale.order :

* **Remise globale TTC en €** : indique un montant final ou une réduction
  totale en euros TTC
* **Remise globale TTC en %** : indique un pourcentage de remise globale TTC

Le module répartit automatiquement la remise au prorata des lignes existantes
en respectant les taux de TVA de chaque ligne. Le total TTC affiché
correspond exactement à ce que tu as négocié.

3 USP différenciants
--------------------

* **USP #1 — Vraiment TTC, pas un trick HT** : l'algorithme calcule en TTC
  net puis répartit en HT, en respectant chaque taux de TVA présent. Pas
  d'arrondi cassé.
* **USP #2 — Compatible factures et commandes** : un seul module pour
  ``sale.order`` ET ``account.move`` (factures clients). Cohérence totale.
* **USP #3 — Imprimable** : le PDF de devis et de facture affiche la remise
  globale TTC explicitement (avant total TTC).

Bénéfices pratiques
-------------------

* Plus de calculatrice mentale pour atteindre un total négocié
* Cohérence entre devis / facture / commande
* Audit trail : la remise est tracée et modifiable
* Compatible multi-TVA (5,5 %, 10 %, 20 % mélangés sur la même commande)

Pour qui ?
----------

* Commerciaux B2C / B2B mixte qui négocient en TTC
* Sites web e-commerce qui appliquent une remise globale sur panier
* Concessionnaires, agencements, prestataires de service à TTC affiché
""",
    "version": "19.0.1.0.0",
    "author": "AB Intelligence Systèmes",
    "maintainer": "Anthony Boursier",
    "website": "https://rmdstore.fr/abis-sale-ttc-remise-globale",
    "license": "OPL-1",
    "category": "Sales",
    # Pricing 249 € : à valider par consult ChatGPT
    "price": 49.99,
    "currency": "EUR",
    "depends": [
        "sale_management",
        "account",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/sale_order_views.xml",
        "views/account_move_views.xml",
        "report/sale_order_report.xml",
        "report/account_move_report.xml",
    ],
    "images": [
        "static/description/banner.png",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}

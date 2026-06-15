# -*- coding: utf-8 -*-
{
    "name": "ABIS Cheque Workflow — Émission, dépôt, encaissement",
    "summary": "Gérez vos chèques bancaires de bout en bout : émission, "
               "remise en banque, encaissement, rejet, relance.",
    "description": """
ABIS Cheque Workflow
=====================

Les paiements par chèque restent majoritaires dans de nombreuses PME
françaises (BTP, services, B2B). Mais Odoo standard offre un suivi limité :
pas de numéro de chèque, pas de remise en banque structurée, pas de relance
sur rejet.

ABIS Cheque Workflow ajoute un modèle ``abis.cheque`` complet avec workflow
métier (émis → en banque → encaissé / rejeté), wizard de remise en banque
groupée, lien automatique vers ``account.payment``, et relances configurables
en cas de rejet bancaire.

Workflow couvert
----------------

1. **Émission** : depuis une facture ou un sale.order, un wizard saisit le
   numéro de chèque, la banque, le titulaire et la date d'émission.
2. **Remise en banque** : un wizard de remise groupée crée un bordereau
   numéroté et passe les chèques en statut "déposé".
3. **Encaissement** : à la réception de l'extrait bancaire, marque les
   chèques encaissés (lien automatique ``account.payment``).
4. **Rejet** : si le chèque est rejeté, relance configurable (mail + activité
   commerciale) et passage en relance / contentieux.
5. **Archive** : historique complet horodaté par chèque.

3 USP différenciants
--------------------

* **USP #1 — Workflow complet de bout en bout** : émission → dépôt →
  encaissement → relance. Toutes les étapes tracées et horodatées.
* **USP #2 — Bordereau de remise en banque** : génère un PDF de bordereau
  prêt-à-imprimer conforme aux standards bancaires français (BNP, CA, BPCE,
  SG, LCL).
* **USP #3 — Relance rejet automatique** : sur rejet bancaire, déclenche
  un workflow de relance (mail client + activité comptable + tag CRM).

Compatibilité
-------------

* Odoo 19.0 Community + Enterprise
* Localisation FR (mais utilisable hors FR)
* Multi-compagnies natif
* Compatible Modules de Comptabilité standard (sans surcharge invasive)

Pour qui ?
----------

* **PME B2B** françaises avec encaissement chèques significatif (> 20% du CA)
* **BTP** (artisans, TPE/PME) où le chèque reste prépondérant
* **Comptables** voulant fiabiliser le rapprochement bancaire
* **Trésoriers** voulant tracer chaque chèque émis ou reçu
""",
    "version": "19.0.1.0.0",
    "author": "AB Intelligence Systèmes",
    "maintainer": "Anthony Boursier",
    "website": "https://rmdstore.fr/abis-cheque-workflow",
    "license": "OPL-1",
    "category": "Accounting",
    # Pricing 149 € : à valider par consult ChatGPT
    "price": 29.99,
    "currency": "EUR",
    "depends": [
        "base",
        "account",
        "mail",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/sequence_data.xml",
        "data/mail_template_data.xml",
        "views/abis_cheque_views.xml",
        "views/abis_cheque_remise_views.xml",
        "views/account_payment_views.xml",
        "views/menu_views.xml",
        "report/cheque_remise_report.xml",
        "wizard/cheque_emit_wizard_views.xml",
    ],
    "images": [
        "static/description/banner.png",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}

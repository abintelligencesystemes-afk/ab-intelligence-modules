# -*- coding: utf-8 -*-
{
    "name": "AB Intelligence — AI Achats (OCR Factures bypass IAP)",
    "summary": "OCR factures fournisseurs via OpenAI Vision + apprentissage progressif (référentiels signatures/produits). Bypass complet des crédits IAP Odoo.",
    "description": """
AB Intelligence — AI Achats
============================

Module OCR factures fournisseurs nouvelle génération :

- **Bypass IAP Odoo** : remplace ``account_invoice_extract`` (crédits IAP) par OpenAI Vision via un Worker Cloudflare propriétaire.
- **Apprentissage progressif** : 3 référentiels (cache hash, signatures fournisseurs, matching produits) qui réduisent le coût IA de 90 % au fil du temps.
- **Bouton « Corriger & Apprendre »** : chaque correction Anthony enrichit le référentiel pour les prochaines factures.
- **Dashboard économies** : visualise le ROI vs IAP Odoo (0,10 €/facture).

Coût cible : 0,015 € → 0,002 € / facture selon la maturité du référentiel
(vs 0,10 € constant IAP Odoo).

Sécurité : License JWT vérifiée à chaque appel, pas de stockage du PDF côté Worker.

Auteur : AB Intelligence Systèmes — Anthony Boursier
Site : https://abintelligence.fr
""",
    "author": "AB Intelligence Systèmes",
    "website": "https://abintelligence.fr",
    "license": "OPL-1",
    "category": "Accounting/Accounting",
    "version": "19.0.0.2.0",
    "depends": [
        "base",
        "mail",
        "account",
        "purchase",
        "stock",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_config_parameter.xml",
        "data/abrmd_ai_initial_suppliers.xml",
        "views/menus.xml",
        "views/abrmd_ai_achat_scan_views.xml",
        "views/abrmd_ai_invoice_cache_views.xml",
        "views/abrmd_ai_supplier_signature_views.xml",
        "views/abrmd_ai_product_match_views.xml",
        "views/account_move_views.xml",
        "views/res_config_settings_views.xml",
        "wizards/abrmd_ai_scan_wizard_views.xml",
    ],
    "images": ["static/description/banner.png"],
    "installable": True,
    "application": True,
    "auto_install": False,
    "price": 696.00,
    "currency": "EUR",
    "support": "support@abintelligence.fr",
}

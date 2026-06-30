# -*- coding: utf-8 -*-
{
    "name": "AI RGPD — Conformité complète (registre, consentements, droits, anonymisation, logs, DPO)",
    "summary": "Met ton Odoo aux normes RGPD en 6 piliers : Article 30, consentements, droits personnes, anonymisation, logs accès, dashboard DPO.",
    "description": """
AB Intelligence Systèmes — AI RGPD V0.2
========================================

Module Odoo de mise en conformité RGPD complète, structuré en 6 piliers :

1. **Registre des activités de traitement (Article 30)** — modèle dédié avec import / export CSV.
2. **Consentements** — capture, retrait, historique horodaté SHA-256, statut par finalité.
3. **Droits des personnes (Articles 12-22)** — workflow demande accès / rectification / effacement / portabilité avec délais légaux (1 mois, prolongeable 2 mois).
4. **Anonymisation et pseudonymisation** — Server Actions pour `res.partner` et modèles personnalisés, hash SHA-256 + sel par tenant.
5. **Logs d'accès aux données sensibles** — modèle dédié + base.automation préconfigurée, recherche par sujet / utilisateur / date.
6. **Dashboard DPO** — vue dashboard avec compteurs, alertes délais légaux, registre Art.30 résumé.

Compatible RGPD strict zone UE. Aucun call-home obligatoire. Compatible audit CNIL.
""",
    "version": "19.0.0.2.1",
    "author": "AB Intelligence Systèmes",
    "maintainer": "Anthony Boursier",
    "website": "https://rmdstore.fr/ai-rgpd",
    "license": "OPL-1",
    "category": "Productivity/Compliance",
    "price": 696.00,
    "currency": "EUR",
    "depends": [
        "base",
        "mail",
    ],
    "data": [
        # Security first
        "security/security.xml",
        "security/ir.model.access.csv",
        # Data
        "data/default_registre_data.xml",
        "data/cron_data.xml",
        "data/ir_actions_server.xml",
        # Views
        "views/menu_views.xml",
        "views/registre_views.xml",
        "views/consent_views.xml",
        "views/request_views.xml",
        "views/access_log_views.xml",
        "views/dashboard_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "demo": [],
    "installable": True,
    "application": True,
    "auto_install": False,
    "post_init_hook": "_post_init_hook",
    "uninstall_hook": "_uninstall_hook",
    "external_dependencies": {
        "python": [],
    },
    "images": [
        "static/description/banner.png",
    ],
}

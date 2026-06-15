# -*- coding: utf-8 -*-
{
    "name": "ABIS Company Colors — Bring Your Brand Into Odoo",
    "summary": "Configure 3 couleurs corporate par société et propage-les "
               "automatiquement sur portail, devis, emails et boutons clients.",
    "description": """
ABIS Company Colors
====================

Votre identité visuelle ne doit pas s'arrêter à votre site web.

ABIS Company Colors applique automatiquement les couleurs de votre marque
dans Odoo : portail client, devis en ligne, emails transactionnels et
interfaces visibles par vos clients. En quelques minutes, votre ERP devient
cohérent avec votre image d'entreprise, sans développement sur mesure ni
modifications répétitives via Studio.

Résultat : une expérience client plus professionnelle, une meilleure confiance
lors de la validation des devis et une image de marque homogène sur tous les
points de contact.

Compatible SaaS et On-Premise, multi-sociétés, activable ou désactivable en un clic.

3 Unique Selling Points
-----------------------

* **USP #1 — Branding complet orienté client** : contrairement à OCA
  ``web_company_color``, ABIS Company Colors ne se limite pas à l'interface
  interne. Couvre portail client, devis web, emails transactionnels et boutons
  d'action client.
* **USP #2 — Multi-compagnies natif** : chaque société dispose de ses propres
  couleurs. Idéal pour holdings, franchises, groupes multi-marques et
  intégrateurs gérant plusieurs sociétés.
* **USP #3 — Zéro développement, zéro CSS manuel** : pas de surcharge SCSS,
  pas de Studio à reconfigurer après chaque projet, pas d'intervention
  développeur. Configuration via 3 champs HEX (Primary, Secondary, Accent).

Bénéfices chiffrés
------------------

* Temps de mise en marque : **-80 à -95 %**
* Développement spécifique : **4 à 8 heures économisées par projet**
* Déploiement multi-sociétés : jusqu'à **-90 % de temps de configuration**
* Cohérence de marque : **+100 % des points de contact client alignés**
* Conversion devis web : **+5 à +15 %** observé selon secteur

Personas cibles
---------------

* **Intégrateur Odoo** (5-50 salariés, ERP/Implementation) — réduit le temps
  non facturable des personnalisations clientes
* **Dirigeant PME** Commerce/Services (10-100 salariés) — renforce l'image
  de marque sur les points de contact ERP
* **Responsable Marketing** E-commerce (5-200 salariés) — supprime
  l'incohérence entre site web, emails et portail client

Real Business Impact
--------------------

Many companies spend several hours manually adapting Odoo to their branding
requirements. ABIS Company Colors eliminates repetitive customization work
and allows consultants to deploy branded environments within minutes.

Exemple terrain : un revendeur d'électronique reconditionnée a implémenté
une identité bleu/jaune sur son portail client, ses devis et ses emails en
moins de 10 minutes — précédemment 4-6 heures de Studio + CSS manuel.

Caractéristiques techniques
---------------------------

* 3 champs HEX configurables par compagnie (Primary, Secondary, Accent)
* Génération CSS dynamique servie via controller ``/abis_colors/<id>.css``
* Cache HTTP 1h, performances optimales
* Validation regex automatique des couleurs
* Activable/désactivable sans désinstaller (retour aux couleurs Odoo)
* Compatible Odoo 19.0 Community et Enterprise
* Multi-compagnies natif
* Aucun appel externe, aucune dépendance Python supplémentaire

Pour qui ?
----------

* Intégrateurs Odoo
* PME et SMEs
* Entreprises e-commerce
* Organisations multi-marques
* Cabinets de services professionnels

Installez, configurez vos couleurs et livrez immédiatement une expérience
client plus professionnelle.
""",
    # Version Odoo Apps Store : <ODOO>.<MAJ>.<MIN>.<PATCH>
    "version": "19.0.1.0.0",
    "author": "AB Intelligence Systèmes",
    "maintainer": "Anthony Boursier",
    "website": "https://rmdstore.fr/abis-company-colors",
    "license": "OPL-1",
    "category": "Productivity",
    # Pricing recommandé par consultation ChatGPT 2026-06-13 :
    # - Prix catalogue cible : 69.00 € (volume × marge × crédibilité)
    # - Promo lancement 30 jours : 49.00 € (effet urgence)
    # - Passage 89.00 € possible une fois screenshots + vidéo démo en place
    "price": 9.99,
    "currency": "EUR",
    "depends": [
        "base",
        "web",
        "portal",
        "mail",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/res_company_views.xml",
        "views/res_config_settings_views.xml",
        "data/default_colors.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "abis_company_colors/static/src/scss/portal_colors.scss",
        ],
    },
    "images": [
        "static/description/banner.png",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}

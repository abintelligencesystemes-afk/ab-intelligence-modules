# -*- coding: utf-8 -*-
{
    "name": "AB Intelligence — Grow Marketing (Anthony Growth Agent)",
    "summary": "Pilotage éditorial multi-canal + vidéo IA low-cost — idées, brouillons, calendrier, médias, patterns, vidéos MP4 générées (TTS + Whisper + FFmpeg).",
    "description": """
AB Intelligence — Grow Marketing
=================================

Module Odoo de pilotage marketing éditorial multi-canal, alimenté par
l'agent IA **Anthony Growth Agent** (OpenAI GPT-4o-mini par défaut).

Fonctionnalités V0.2
--------------------
* Pipeline complet **idée → brouillon IA → validation → planning → publication**.
* Modèle ``abrmd.grow.idea`` : file d'idées avec workflow proposed →
  approved → used / rejected. Cron quotidien (07h UTC) propose 3 idées /
  jour basées sur les top patterns marketing et un produit ou une tâche.
* Modèle ``abrmd.grow.post`` : posts pour LinkedIn, Instagram, Facebook,
  X, YouTube, Threads, TikTok. Limites de caractères par canal,
  régénération de brouillon, tracking publication (URL + date).
* Modèle ``abrmd.grow.media`` : bibliothèque médias (images, vidéos),
  imports depuis iCloud Drive (instance self-hostée) ou upload manuel.
* Modèles ``abrmd.grow.pattern`` + ``abrmd.grow.veille.video`` :
  patterns marketing dominants (hook / CTA / structure) avec score
  composite (engagement × récence). Veille top vidéos pour alimenter
  les patterns automatiquement (V0.3).
* **Couche vidéo low-cost** : modèle ``abrmd.grow.video`` qui orchestre
  OpenAI TTS (voix off ~0.014€ / 1k chars) + Whisper (transcription
  ~0.0055€/min) + **FFmpeg** (montage gratuit, subprocess).
  Sortie MP4 verticale 9:16 / 16:9 / 1:1 / 4:5 avec sous-titres burnés.
  Cron de fond `cron_process_pending_videos` traite la file en
  background. Coût visé : ~0,05€ par vidéo.
* Wizards : génération de post IA (3 propositions), génération de
  vidéo MP4, import médias iCloud.
* Vues complètes : kanban, list, form, calendar, gallery médias,
  search avec filtres et group-by.

Modes de déploiement
--------------------
* **Module Python (apps.odoo.com)** : pour clients on-premise — tout
  fonctionne nativement (FFmpeg via subprocess sur l'hôte Odoo).
* **SaaS Odoo Online (rmd-store)** : pas de filesystem hôte ni de
  FFmpeg → mode hybride avec agent local Mac (script Python standalone
  qui appelle FFmpeg sur le Mac d'Anthony et upload le MP4 via
  ``ir.attachment``). Documentation dans le README.

Compatibilité abi-control-plane
-------------------------------
* ``post_init_hook`` : ping le control plane à l'install.
* ``uninstall_hook`` : notifie la désinstall.
* Cron telemetry quotidien (compteurs anonymes, RGPD-safe).
* Cron check_update quotidien (notification + kill switch distant).
* Kill switch local via ``ir.config_parameter``
  ``abrmd_grow_marketing.killed``.

Sécurité & RGPD
---------------
* Aucune FK obligatoire vers res.users / res.partner dans les modèles métier.
* Clé API OpenAI en ir.config_parameter (à protéger côté hébergeur).
* Aucun secret commit (test pure-python ``test_no_api_key_in_clear_in_source``).
* Telemetry : URL Odoo + UUID instance + compteurs, JAMAIS de contenu post.
* Veille vidéos : creator_handle hashable SHA256 sur demande.

Stack vidéo low-cost
--------------------
* Script + caption : OpenAI GPT-4o-mini (~0.001€ / post)
* Voix off : OpenAI TTS voix nova/alloy/echo/fable/onyx/shimmer
* Transcription : OpenAI Whisper API
* Montage : FFmpeg natif (subprocess Python)
* Génération vidéo from text (Runway/Sora) : ❌ skippé V0.2,
  trop cher pour démarrer.
""",
    "author": "AB Intelligence — Anthony Boursier",
    "website": "https://rmd-store.com",
    "support": "contact@rmdsto.re",
    "license": "LGPL-3",
    "category": "Marketing/Social Marketing",
    "version": "19.0.0.2.0",
    "depends": [
        "base",
        "mail",
        "web",
        "product",
        "project",
        "sale",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_config_parameter.xml",
        "data/cron.xml",
        "views/abrmd_grow_post_views.xml",
        "views/abrmd_grow_idea_views.xml",
        "views/abrmd_grow_media_views.xml",
        "views/abrmd_grow_pattern_views.xml",
        "views/abrmd_grow_video_views.xml",
        "views/product_template_views.xml",
        "views/project_task_views.xml",
        "views/res_config_settings.xml",
        "wizard/abrmd_grow_generate_wizard_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "abrmd_grow_marketing/static/src/js/grow_post_preview.js",
            "abrmd_grow_marketing/static/src/xml/grow_post_preview.xml",
            "abrmd_grow_marketing/static/src/scss/grow_post.scss",
        ],
    },
    "images": [
        "static/description/banner.png",
        "static/description/icon.png",
    ],
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
    "installable": True,
    "application": True,
    "auto_install": False,
}

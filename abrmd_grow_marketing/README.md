# abrmd_grow_marketing — AB Intelligence Grow Marketing

> Module Odoo v19 — pilotage éditorial multi-canal (LinkedIn, Instagram,
> Facebook, X/Twitter, YouTube, Threads, TikTok) **+ génération vidéo IA
> low-cost** (OpenAI TTS + Whisper + FFmpeg), alimenté par
> **Anthony Growth Agent**.

**Version V0.2 — 2026-05-23.**

## Statut V0.2

Tout est branché et testable localement :

- Workflow complet **idée → brouillon → validation → planning → publication**
- Cron quotidien (07h UTC) qui propose 3 idées de posts chaque matin
- Wizard de génération IA (3 propositions, choix radio, audit complet)
- Pipeline vidéo MP4 low-cost intégré (cron de fond, ~0,05€ / vidéo)
- 28+ tests pure-python verts (`./run_tests.sh`)

## Stack vidéo low-cost (V0.2)

| Brique | Provider | Coût indicatif |
|---|---|---|
| Script + caption | OpenAI GPT-4o-mini | ~0,001 € / post |
| Voix off | OpenAI TTS (nova / alloy / echo / fable / onyx / shimmer) | ~0,014 € / 1k chars |
| Transcription | OpenAI Whisper API | ~0,0055 € / minute |
| Montage MP4 | FFmpeg natif (subprocess) | 0 € |
| Génération vidéo from text (Runway / Sora) | skippé V0.2 | — |

**Coût total estimé : ~0,05 € par vidéo.**

## Modes de déploiement

### Mode A — Module Python on-premise (apps.odoo.com)

Pour clients PME qui auto-hébergent Odoo : installe le module classique
depuis apps.odoo.com. FFmpeg doit être disponible sur l'hôte
(`apt install ffmpeg` sur Debian/Ubuntu, `brew install ffmpeg` sur macOS).

Tout fonctionne nativement : `cron_process_pending_videos` traite les
vidéos en background toutes les 5 minutes.

### Mode B — Odoo SaaS Online (ex. rmd-store.odoo.com)

Limitation Odoo Online : pas d'install de modules Python custom + pas
de FFmpeg sur l'hôte. Solution hybride :

1. **Modèles Studio** — recrée `x_abrmd_grow_post`, `x_abrmd_grow_idea`,
   `x_abrmd_grow_media`, `x_abrmd_grow_video` avec les mêmes champs.
2. **JS asset étendu** — étend l'asset existant (8247) pour proposer
   "Choisir une idée" + "Générer brouillon IA" depuis le widget.
3. **Agent local Mac** — script Python standalone tournant en background
   (launchd) sur le Mac d'Anthony qui :
   - poll régulièrement `x_abrmd_grow_video` en state `generating`
   - télécharge le script + médias
   - appelle OpenAI TTS + Whisper + FFmpeg local
   - upload le MP4 via `ir.attachment` puis met le record à `ready`

L'agent local est un script à déployer séparément (voir
`Script-Deploiement-SaaS-v19.2.md` dans iCloud Knowledge).

## Tests

```bash
cd abrmd_grow_marketing
pip install pytest --break-system-packages
./run_tests.sh
```

28+ tests pure-python (manifest, security, hooks, anti-secret, pipeline
vidéo helpers, char limits par canal, workflows idée / vidéo).

## Structure

```
abrmd_grow_marketing/
├── __manifest__.py
├── __init__.py
├── hooks.py
├── README.md
├── CHANGELOG.md
├── LICENSE.txt
├── models/
│   ├── abrmd_grow_post.py
│   ├── abrmd_grow_idea.py
│   ├── abrmd_grow_media.py
│   ├── abrmd_grow_pattern.py
│   ├── abrmd_grow_veille_video.py
│   ├── abrmd_grow_video.py
│   ├── abrmd_grow_video_pipeline.py
│   ├── abrmd_grow_proposer.py
│   ├── abrmd_grow_telemetry.py
│   ├── product_template.py
│   ├── project_task.py
│   └── res_config_settings.py
├── wizard/
│   ├── abrmd_grow_generate_wizard.py
│   ├── abrmd_grow_generate_wizard_views.xml
│   └── abrmd_grow_video_wizard.py
├── views/
│   ├── abrmd_grow_post_views.xml
│   ├── abrmd_grow_idea_views.xml
│   ├── abrmd_grow_media_views.xml
│   ├── abrmd_grow_pattern_views.xml
│   ├── abrmd_grow_video_views.xml
│   ├── product_template_views.xml
│   ├── project_task_views.xml
│   └── res_config_settings.xml
├── data/
│   ├── ir_config_parameter.xml
│   └── cron.xml
├── security/
│   └── ir.model.access.csv
├── static/description/
│   ├── icon.png (128×128)
│   ├── banner.png (1024×256)
│   └── index.html
├── static/src/
│   ├── js/grow_post_preview.js
│   ├── xml/grow_post_preview.xml
│   └── scss/grow_post.scss
├── i18n/
│   ├── fr.po
│   └── en.po
├── tests/                    (TransactionCase Odoo)
└── tests_pure/               (pytest sans Odoo)
```

## Configuration

Une fois installé, va dans **Configuration → Paramètres généraux →
AB Intelligence Grow Marketing** :

1. Renseigne la clé API OpenAI (`ir.config_parameter` `openai.api_key`).
2. Choisis le modèle GPT par défaut (gpt-4o-mini conseillé).
3. Active / désactive via le kill switch si besoin.

## Roadmap

- **V0.2 (cette release)** — pipeline complet, vidéo low-cost intégrée
- V0.3 — Veille YouTube Data API live, ElevenLabs, Runway / Sora
- V0.4 — Publication semi-auto (Buffer / Hootsuite), analytics

## Licence

LGPL-3 — module gratuit (acquisition de leads AB Intelligence Systèmes).

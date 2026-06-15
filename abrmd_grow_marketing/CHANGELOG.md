# Changelog — abrmd_grow_marketing

Format : [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/).

## [19.0.0.2.0] — 2026-05-23

### Ajouté
- **Workflow complet idée → brouillon → validation → planning → publication.**
- Modèle `abrmd.grow.idea` avec workflow proposed → approved → used / rejected
  et lien O2M vers les posts générés.
- Modèle `abrmd.grow.media` (bibliothèque images/vidéos) + wizard
  "Importer depuis iCloud Drive" (instance self-hostée).
- Modèle `abrmd.grow.pattern` avec composite_score et recency_weight calculé.
- Modèle `abrmd.grow.veille.video` avec contrainte unique (platform, external_id)
  et anonymisation SHA256 du creator_handle.
- Modèle `abrmd.grow.tag` partagé entre idées et médias.
- **Couche vidéo low-cost** :
  - Modèle `abrmd.grow.video` (lié au post) avec workflow draft → generating
    → ready / failed.
  - AbstractModel `abrmd.grow.video.pipeline` qui orchestre OpenAI TTS +
    OpenAI Whisper + FFmpeg en subprocess.
  - Sortie MP4 verticale 9:16 / 16:9 / 1:1 / 4:5 avec sous-titres burnés.
  - Cron `cron_process_pending_videos` toutes les 5 minutes.
  - Estimation coût pure-python (~0,05€ par vidéo, sanity check).
  - Wizard `abrmd.grow.video.wizard` avec preview coût temps réel.
- Wizard de génération IA passé en **mode live** :
  - Appel OpenAI Chat Completions réel (urllib std-lib).
  - 3 propositions cliquables avec choix radio + régénération.
  - Stockage prompt + réponse brute en audit sur le post.
  - Fallback stub explicite si pas de clé API.
- Cron `cron_propose_daily_ideas` 07h UTC qui propose 3 idées chaque jour
  avec mail récap à contact@rmdsto.re (best-effort, non bloquant).
- Champs étendus sur `abrmd.grow.post` :
  - `idea_id`, `pattern_ids`, `media_ids`, `partner_id`
  - `published_date`, `published_url`, `ai_model`, `ai_response_raw`,
    `ai_objectif`
  - `char_limit_canal`, `over_limit` computed (limites par canal :
    LinkedIn 3000, Twitter 280, TikTok/Instagram 2200, etc.)
  - Bouton `action_regenerate_draft` qui ré-ouvre le wizard avec contexte.
- Vues complètes :
  - Menu racine "Grow Marketing" avec sous-menus Idées / Posts / Médias /
    Vidéos / Patterns / Veille / Configuration.
  - Kanban Idées groupé par state, kanban Posts groupé par state.
  - Gallery médias avec vignettes.
  - Calendrier éditorial.
  - Search views riches avec filtres et group-by.
- 28+ tests pure-python (couverture manifest, security, pipeline vidéo
  helpers, char limits, workflows, media mimetype, wizard parse_proposals,
  cron declarations).

### Modifié
- **Licence : OEEL-1 → LGPL-3** (gratuit, acquisition leads AB Intelligence).
- Version : 19.0.0.1.0 → 19.0.0.2.0.
- `depends` : ajout de `sale`.
- README + index.html marketing mis à jour pour V0.2.
- run_tests.sh patche désormais tous les test_*.py (plus uniquement test_minimal).

### Sécurité
- Aucun nouveau secret commit (test pure-python qui vérifie).
- Kill switch global appliqué à : cron_check_due, cron_propose_daily_ideas,
  cron_process_pending_videos.
- Pas de FK obligatoire vers res.users / res.partner sur les nouveaux modèles.
- Anonymisation SHA256 du creator_handle sur les vidéos veille.

### Connu / limites
- Mode SaaS Odoo Online (rmd-store.odoo.com) : modèles Studio +
  agent local Mac à déployer séparément (procédure dans iCloud).
- Veille YouTube Data API : skippée cette release (V0.3).
- Génération vidéo from text (Runway / Sora) : skippée (trop chère pour
  démarrage low-cost).
- Mail récap quotidien : utilise `mail.mail` standard, non bloquant si SMTP HS.

## [19.0.0.1.0] — 2026-05-20

### Ajouté
- Module initial V0.1 — squelette propre.
- Modèle `abrmd.grow.post` (titre, contenu, canal, scheduled_date,
  published, visual, product_id, project_id, task_id, state).
- Vues list, form, kanban, calendar, search.
- Bouton "Générer post Grow" sur product.template et project.task.
- Wizard `abrmd.grow.generate.wizard` avec preview stub (intégration OpenAI
  commentée pour V0.2).
- Cron quotidien `cron_check_due`.
- Settings page (clé OpenAI, modèle GPT, kill switch).
- Hooks post_init / uninstall vers abi-control-plane.
- Telemetry abstract model + cron heartbeat + cron check_update.
- Widget Owl `PostPreview` avec live char count.
- Tests pure-python (5+ verts).
- Documentation README, index.html marketing.

### Sécurité
- Pas de FK obligatoire vers res.users / res.partner.
- Clé OpenAI en `ir.config_parameter`.
- Aucun secret commit.

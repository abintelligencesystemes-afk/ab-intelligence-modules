# Changelog — abrmd_ai_rgpd

## v0.2.0 — 2026-05-27

### Added
- **Pilier 1 — Registre Art.30** : modèle `abrmd.rgpd.registre` complet (responsable, finalité, base légale, données, durée, sécurité, transferts hors UE).
- **Pilier 2 — Consentements** : modèle `abrmd.rgpd.consent` avec workflow given → withdrawn → expired, hash SHA-256 + sel, cron d'expiration auto.
- **Pilier 3 — Droits personnes** : modèle `abrmd.rgpd.request` avec 7 types de demandes (Art.15-22), workflow complet, délais légaux calculés (1 mois + 2 mois prolongation), cron d'alerte à J-7.
- **Pilier 4 — Anonymisation** : AbstractModel `abrmd.rgpd.anonymizer` avec helpers email/phone/IP, Server Actions sur res.partner (pseudonymiser réversible + anonymiser définitif).
- **Pilier 5 — Logs d'accès** : modèle `abrmd.rgpd.access.log` avec API `log_access()`, 10 types d'opérations, marquage données sensibles, cron de purge auto.
- **Pilier 6 — Dashboard DPO** : TransientModel `abrmd.rgpd.dashboard` avec 10 KPIs + alertes contextuelles.

### Changed
- License OEEL-1 → LGPL-3 (leadgen AB Intelligence Systèmes)
- Catégorie : Productivity → Productivity/Compliance

### Tests
- 12 tests TransactionCase ajoutés (4 consent, 5 request, 6 anonymizer)

### Migration depuis v0.1.0
- Pas de migration de données — v0.2.0 est un module complémentaire, peut coexister avec un éventuel chatbot RGPD v0.1.

## v0.1.0 — 2026-05-19

### Added
- Chatbot IA RGPD-strict (Mistral FR / Claude EU / OpenAI EU / Llama)
- Hooks abi-control-plane
- 9 tests pure-python verts

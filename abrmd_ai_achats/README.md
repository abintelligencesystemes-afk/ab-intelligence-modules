# abrmd_ai_achats v0.2.0

**Module Odoo 19** — OCR factures fournisseurs via OpenAI Vision + apprentissage progressif.

Bypass complet des crédits IAP Odoo (`account_invoice_extract`).

## Architecture

```
account.move (draft)
    │ clic "OCR via OpenAI"
    ▼
abrmd.ai.achat.scan ─────► services.learning.run_pipeline
    │                          │
    │                          ├─ 1. lookup abrmd.ai.invoice.cache (hash SHA256)
    │                          │     hit → retour direct (0 €)
    │                          │
    │                          ├─ 2. (v0.3) signature fournisseur → contexte enrichi
    │                          │
    │                          └─ 3. POST Worker abi-control-plane /api/ocr/invoice
    │                                 │
    │                                 ▼
    │                              OpenAI Vision gpt-4o → JSON
    │                                 │
    │                                 ▼
    │                              cache write (hash → JSON)
    ▼
extracted_data parsé → pré-remplissage facture
    │ clic "Corriger & Apprendre" après vérif Anthony
    ▼
- abrmd.ai.supplier.signature.learn_or_update (occurrences++)
- abrmd.ai.product.match.learn (pour chaque ligne corrigée)
```

## Modèles

| Modèle | Rôle |
|---|---|
| `abrmd.ai.achat.scan` | Historique de chaque scan (audit + traçabilité coût) |
| `abrmd.ai.invoice.cache` | Cache hash SHA256 → JSON (évite repayer pour même fichier) |
| `abrmd.ai.supplier.signature` | Référentiel signatures fournisseurs (apprentissage) |
| `abrmd.ai.product.match` | Référentiel matching produits (apprentissage le + payant LT) |

## Configuration (Settings → AI Achats)

| Paramètre | Défaut | Description |
|---|---|---|
| `abrmd_ai_achats.worker_url` | `https://abi-control-plane.workers.dev/api/ocr/invoice` | Endpoint Worker |
| `abrmd_ai_achats.license_key` | (vide) | JWT émis par Stripe checkout |
| `abrmd_ai_achats.instance_uuid` | (vide) | UUID v4 unique de l'instance |
| `abrmd_ai_achats.signature_threshold` | 0.8 | Similarité min match signature |
| `abrmd_ai_achats.product_match_threshold` | 0.8 | Similarité min match produit |
| `abrmd_ai_achats.openai_model` | gpt-4o | Modèle utilisé |
| `abrmd_ai_achats.killed` | False | Kill switch urgence |

## Sécurité

- License JWT vérifiée à chaque appel Worker (réutilise le mécanisme `/api/verify`)
- Rate limit 60 req/min par instance côté Worker
- Pas de stockage du PDF côté Worker (in-memory only, file OpenAI supprimé après extraction)
- OPENAI_API_KEY jamais exposée à l'instance Odoo (gérée par le Worker)

## Tests

```bash
odoo-bin -d testdb -i abrmd_ai_achats --test-tags abrmd_ai_achats --stop-after-init
```

3 fichiers de tests :
- `test_signature_matcher.py` — match/learn signatures fournisseurs
- `test_product_matcher.py` — match exact ref / fuzzy nom / learn
- `test_learning.py` — pipeline cache hit (sans appel Worker)

## Installation

### Odoo on-premise / Odoo.sh

1. Copier le dossier `abrmd_ai_achats/` dans `addons/` ou `extra-addons/`
2. Apps → Update Apps List → AB Intelligence — AI Achats → Install
3. Settings → AI Achats → renseigner `license_key`, `instance_uuid`, `worker_url`

### Odoo SaaS Online (rmd-store.odoo.com)

→ Voir `PROCEDURE-Studio-rmd-store-Anthony.md` (configuration manuelle Studio équivalente).

## Roadmap

- v0.2.1 — Dashboard stats économies (Studio Pivot)
- v0.3.0 — Pré-extraction texte avant Vision (signature match avant appel)
- v0.4.0 — Publication apps.odoo.com (screenshots, demo data, EULA)

## License

OPL-1 — propriétaire AB Intelligence Systèmes.

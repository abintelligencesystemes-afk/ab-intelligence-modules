# abis_search_normalize — Recherche partenaires sans accents

Recherche partenaires Odoo **insensible aux accents, à la casse et à la
ponctuation**, avec **index PostgreSQL pg_trgm** pour fuzzy search rapide.

## Fonctionnalités

- Tape `francois dupont` → trouve `François Dupont`, `FRANCOIS DUPONT`, etc.
- Recherche unifiée sur `name`, `email`, `phone`, `ref`
- Index PostgreSQL trigram (pg_trgm) installé automatiquement
- Surcharge `_name_search` Odoo pour autocomplete et @mentions
- Compatible Community + Enterprise
- Multi-compagnies natif

## Installation

1. Apps → cherche "ABIS Search Normalize"
2. Installe
3. Le post_init_hook active pg_trgm et crée l'index GIN automatiquement
4. À l'installation, Odoo recompute `name_normalized` sur tous les partenaires existants

## Compatibilité PostgreSQL

Requiert PostgreSQL ≥ 9.6 (extension pg_trgm).
Odoo SaaS : extension déjà disponible.
Self-hosted : nécessite `CREATE EXTENSION` autorisé (super-user au moins une fois).

## Tarification

99.00 € (achat unique OPL-1).

## Support

- Email : contact@rmdsto.re
- Web : https://rmdstore.fr/abis-search-normalize

## Auteur

AB Intelligence Systèmes — Anthony Boursier

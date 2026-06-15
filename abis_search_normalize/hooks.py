# -*- coding: utf-8 -*-
"""Hooks d'installation : crée extension pg_trgm et index GIN."""
import logging

_logger = logging.getLogger(__name__)


def _post_init_create_pg_trgm(env):
    """Active l'extension PostgreSQL pg_trgm + index GIN sur name_normalized."""
    cr = env.cr
    try:
        cr.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
        _logger.info("abis_search_normalize : extension pg_trgm OK")
    except Exception as exc:
        _logger.warning(
            "abis_search_normalize : impossible de créer pg_trgm (privilèges ?) : %s",
            exc,
        )
        return
    # Index GIN trigram pour recherche fuzzy
    cr.execute(
        """
        CREATE INDEX IF NOT EXISTS res_partner_name_normalized_trgm_idx
        ON res_partner USING gin (name_normalized gin_trgm_ops);
        """
    )
    _logger.info("abis_search_normalize : index trigram installé")


def _uninstall_drop_pg_trgm(env):
    """Supprime l'index trigram (laisse l'extension pour d'autres modules)."""
    env.cr.execute(
        "DROP INDEX IF EXISTS res_partner_name_normalized_trgm_idx;"
    )
    _logger.info("abis_search_normalize : index trigram supprimé")

# -*- coding: utf-8 -*-
"""Hooks d'installation/désinstallation pour abrmd_ai_rgpd v0.2.

Compatible abi-control-plane (heartbeat install / uninstall).
Aucun call-home obligatoire : la télémétrie est opt-in via Settings.
"""
import logging

_logger = logging.getLogger(__name__)


def _safe_ping(env, event):
    """Envoie un ping anonymisé au control-plane si la télémétrie est activée.

    En cas d'erreur réseau, ne bloque jamais l'install/uninstall.
    """
    try:
        params = env["ir.config_parameter"].sudo()
        telemetry_enabled = params.get_param("abrmd_ai_rgpd.telemetry_enabled", "False") == "True"
        if not telemetry_enabled:
            _logger.info("abrmd_ai_rgpd: telemetry disabled, skipping %s ping", event)
            return
        # Le payload est anonymisé : pas de res.users, pas de res.partner, pas d'IP.
        # Compteurs only.
        registry_count = env["abrmd.rgpd.registre"].sudo().search_count([])
        consent_count = env["abrmd.rgpd.consent"].sudo().search_count([])
        request_count = env["abrmd.rgpd.request"].sudo().search_count([])
        _logger.info(
            "abrmd_ai_rgpd %s ping payload: registries=%d consents=%d requests=%d",
            event, registry_count, consent_count, request_count,
        )
        # NB: l'envoi HTTP est volontairement à brancher côté ResConfigSettings
        # pour rester contrôlable par l'admin.
    except Exception as exc:  # pylint: disable=broad-except
        _logger.warning("abrmd_ai_rgpd %s safe_ping failed silently: %s", event, exc)


def _post_init_hook(env):
    _safe_ping(env, "install")


def _uninstall_hook(env):
    _safe_ping(env, "uninstall")

# -*- coding: utf-8 -*-
"""Install / uninstall hooks — ping abi-control-plane.

Endpoint backend (à confirmer en V0.2) : https://abi-control.rmd-store.com/v1/
En dev : valeur surchargeable via ``ir.config_parameter``
``abrmd_grow_marketing.control_plane_url``.
"""
import logging

_logger = logging.getLogger(__name__)


def _safe_ping(env, event):
    """Envoie un ping RGPD-safe au control plane (jamais bloquant)."""
    try:
        env["abrmd.grow.telemetry"]._send_event(event)
    except Exception as exc:  # noqa: BLE001
        _logger.warning(
            "[abrmd_grow_marketing] ping %s a échoué (non bloquant) : %s",
            event, exc,
        )


def post_init_hook(env):
    """Appelé à l'install — Odoo 17+ signature (env)."""
    _logger.info("[abrmd_grow_marketing] post_init_hook — ping install")
    _safe_ping(env, "install")


def uninstall_hook(env):
    """Appelé au moment de la désinstall."""
    _logger.info("[abrmd_grow_marketing] uninstall_hook — ping uninstall")
    _safe_ping(env, "uninstall")

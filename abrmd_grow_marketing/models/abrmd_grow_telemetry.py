# -*- coding: utf-8 -*-
"""Telemetry / control-plane bridge — RGPD-safe.

Aucun contenu de post n'est envoyé. Seulement :
 * UUID instance (généré 1 fois, stocké local)
 * Version module
 * Compteurs anonymes (nb posts période, répartition canaux, kill switch state)
 * URL Odoo (web.base.url)
"""
import json
import logging
import uuid

from odoo import api, fields, models

try:
    import urllib.request as _urlreq  # std-lib, pas de dep externe
    import urllib.error as _urlerr  # noqa: F401
except Exception:  # pragma: no cover
    _urlreq = None

_logger = logging.getLogger(__name__)

MODULE_VERSION = "19.0.0.1.0"
MODULE_TECHNICAL_NAME = "abrmd_grow_marketing"
DEFAULT_CONTROL_PLANE_URL = "https://abi-control.rmd-store.com/v1"


class AbrmdGrowTelemetry(models.AbstractModel):
    _name = "abrmd.grow.telemetry"
    _description = "abrmd_grow_marketing telemetry & control-plane bridge"

    # ------------------------------------------------------------------
    # Helpers internes
    # ------------------------------------------------------------------
    @api.model
    def _get_or_create_instance_uuid(self):
        ICP = self.env["ir.config_parameter"].sudo()
        key = f"{MODULE_TECHNICAL_NAME}.instance_uuid"
        instance_uuid = ICP.get_param(key)
        if not instance_uuid:
            instance_uuid = str(uuid.uuid4())
            ICP.set_param(key, instance_uuid)
        return instance_uuid

    @api.model
    def _get_control_plane_url(self):
        ICP = self.env["ir.config_parameter"].sudo()
        return ICP.get_param(
            f"{MODULE_TECHNICAL_NAME}.control_plane_url",
            default=DEFAULT_CONTROL_PLANE_URL,
        )

    @api.model
    def _get_base_url(self):
        return self.env["ir.config_parameter"].sudo().get_param(
            "web.base.url", default="unknown"
        )

    @api.model
    def _http_post_json(self, url, payload, timeout=5):
        """POST JSON minimaliste (std-lib uniquement). Retourne dict ou None."""
        if _urlreq is None:
            _logger.warning("[abrmd_grow_marketing] urllib indisponible")
            return None
        data = json.dumps(payload).encode("utf-8")
        req = _urlreq.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": f"{MODULE_TECHNICAL_NAME}/{MODULE_VERSION}",
            },
            method="POST",
        )
        try:
            with _urlreq.urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode("utf-8") or "{}"
                return json.loads(body)
        except Exception as exc:  # noqa: BLE001
            _logger.info(
                "[abrmd_grow_marketing] control-plane POST %s — non joignable : %s",
                url, exc,
            )
            return None

    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------
    @api.model
    def _send_event(self, event_name, extra=None):
        payload = {
            "event": event_name,
            "module": MODULE_TECHNICAL_NAME,
            "version": MODULE_VERSION,
            "instance_uuid": self._get_or_create_instance_uuid(),
            "base_url": self._get_base_url(),
        }
        if extra:
            payload.update(extra)
        url = f"{self._get_control_plane_url().rstrip('/')}/events"
        return self._http_post_json(url, payload)

    @api.model
    def cron_send_telemetry(self):
        """Cron quotidien — compteurs anonymes."""
        Post = self.env["abrmd.grow.post"]
        count_total = Post.search_count([])
        count_published = Post.search_count([("published", "=", True)])
        # Répartition par canal (anonyme)
        canals = {}
        for canal_key, _label in Post._fields["canal"].selection:
            canals[canal_key] = Post.search_count([("canal", "=", canal_key)])
        ICP = self.env["ir.config_parameter"].sudo()
        killed = ICP.get_param(
            f"{MODULE_TECHNICAL_NAME}.killed", default="False"
        ) == "True"
        extra = {
            "posts_total": count_total,
            "posts_published": count_published,
            "by_canal": canals,
            "killed": killed,
        }
        return self._send_event("heartbeat", extra)

    @api.model
    def cron_check_update(self):
        url = f"{self._get_control_plane_url().rstrip('/')}/updates/{MODULE_TECHNICAL_NAME}"
        payload = {
            "module": MODULE_TECHNICAL_NAME,
            "current_version": MODULE_VERSION,
            "instance_uuid": self._get_or_create_instance_uuid(),
        }
        resp = self._http_post_json(url, payload)
        if not resp:
            return False
        ICP = self.env["ir.config_parameter"].sudo()
        if "killed" in resp:
            ICP.set_param(
                f"{MODULE_TECHNICAL_NAME}.killed",
                "True" if resp["killed"] else "False",
            )
        latest = resp.get("latest_version")
        if latest and latest != MODULE_VERSION:
            ICP.set_param(f"{MODULE_TECHNICAL_NAME}.update_available", latest)
            _logger.info(
                "[abrmd_grow_marketing] Nouvelle version dispo : %s (actuelle %s)",
                latest, MODULE_VERSION,
            )
        return resp

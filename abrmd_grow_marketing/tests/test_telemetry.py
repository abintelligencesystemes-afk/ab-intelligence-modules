# -*- coding: utf-8 -*-
"""Tests télémétrie abrmd_grow_marketing."""
try:
    from odoo.tests.common import TransactionCase, tagged
except Exception:  # pragma: no cover
    TransactionCase = object

    def tagged(*args, **kwargs):
        def deco(cls):
            return cls
        return deco


@tagged("post_install", "-at_install")
class TestGrowTelemetry(TransactionCase):
    def test_instance_uuid_stable(self):
        Tel = self.env["abrmd.grow.telemetry"]
        u1 = Tel._get_or_create_instance_uuid()
        u2 = Tel._get_or_create_instance_uuid()
        self.assertEqual(u1, u2)
        self.assertEqual(len(u1), 36)

    def test_control_plane_url_default(self):
        Tel = self.env["abrmd.grow.telemetry"]
        url = Tel._get_control_plane_url()
        self.assertTrue(url.startswith("http"))

    def test_send_event_non_blocking(self):
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("abrmd_grow_marketing.control_plane_url", "http://127.0.0.1:1/v1")
        Tel = self.env["abrmd.grow.telemetry"]
        result = Tel._send_event("install")
        self.assertIsNone(result)

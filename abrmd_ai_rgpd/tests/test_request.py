# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import fields
from odoo.tests import common, tagged
from odoo.exceptions import UserError


@tagged("post_install", "-at_install", "abrmd_rgpd")
class TestRequest(common.TransactionCase):

    def _create(self, **kw):
        defaults = {
            "request_type": "access",
            "subject_name": "Alice Tester",
            "subject_email": "alice@test.local",
        }
        defaults.update(kw)
        return self.env["abrmd.rgpd.request"].create(defaults)

    def test_sequence_generated(self):
        r = self._create()
        self.assertTrue(r.name.startswith("RGPD-REQ-"))

    def test_deadline_computed(self):
        r = self._create()
        self.assertTrue(r.deadline_date)
        # Default 30 days
        delta = (r.deadline_date - r.received_date).days
        self.assertGreaterEqual(delta, 29)
        self.assertLessEqual(delta, 31)

    def test_workflow_full(self):
        r = self._create()
        r.action_mark_received()
        self.assertEqual(r.state, "received")
        # Should fail without verification method
        with self.assertRaises(UserError):
            r.action_identity_verified()
        r.identity_verification_method = "Copie carte identité reçue par email"
        r.action_identity_verified()
        self.assertEqual(r.state, "in_progress")
        self.assertTrue(r.identity_verified)
        # Close requires response
        with self.assertRaises(UserError):
            r.action_close_done()
        r.response = "<p>Voici les données vous concernant.</p>"
        r.action_close_done()
        self.assertEqual(r.state, "done")
        self.assertTrue(r.closed_date)

    def test_extend_deadline_requires_reason(self):
        r = self._create()
        r.action_mark_received()
        with self.assertRaises(UserError):
            r.action_extend_deadline()
        r.extension_reason = "Volume des données à exporter > 10000 lignes."
        old_deadline = r.deadline_date
        r.action_extend_deadline()
        self.assertEqual(r.state, "extended")
        self.assertGreater((r.deadline_date - old_deadline).days, 50)

    def test_overdue_detection(self):
        r = self._create()
        r.received_date = fields.Datetime.now() - timedelta(days=40)
        # Recompute
        r._compute_deadline_date()
        r._compute_days_to_deadline()
        self.assertTrue(r.is_overdue)

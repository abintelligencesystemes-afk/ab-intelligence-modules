# -*- coding: utf-8 -*-
from odoo.tests import common, tagged


@tagged("post_install", "-at_install", "abrmd_rgpd")
class TestAnonymizer(common.TransactionCase):

    def setUp(self):
        super().setUp()
        self.anonymizer = self.env["abrmd.rgpd.anonymizer"]
        # Set a known salt for reproducible tests
        self.env["ir.config_parameter"].sudo().set_param(
            "abrmd_ai_rgpd.anonymization_salt", "test-salt-1234"
        )

    def test_pseudonymize_stable(self):
        h1 = self.anonymizer.pseudonymize("alice@test.local")
        h2 = self.anonymizer.pseudonymize("ALICE@test.local")
        self.assertEqual(h1, h2)
        self.assertEqual(len(h1), 64)

    def test_pseudonymize_unique(self):
        h1 = self.anonymizer.pseudonymize("alice@test.local")
        h2 = self.anonymizer.pseudonymize("bob@test.local")
        self.assertNotEqual(h1, h2)

    def test_anonymize_email(self):
        self.assertEqual(
            self.anonymizer.anonymize_email("alice@test.local"),
            "a***@test.local",
        )
        self.assertEqual(
            self.anonymizer.anonymize_email("a@test.local"),
            "*@test.local",
        )

    def test_anonymize_phone(self):
        self.assertEqual(
            self.anonymizer.anonymize_phone("+33 6 12 34 56 78"),
            "33********78",
        )

    def test_anonymize_ipv4(self):
        self.assertEqual(
            self.anonymizer.anonymize_ip("192.168.1.42"),
            "192.168.1.0/24",
        )

    def test_anonymize_ipv6(self):
        self.assertTrue(
            self.anonymizer.anonymize_ip("2001:db8::1").startswith("2001:db8:")
        )

    def test_anonymize_partner(self):
        partner = self.env["res.partner"].create({
            "name": "Alice Dupont",
            "email": "alice@test.local",
            "phone": "+33 6 12 34 56 78",
            "comment": "Note privée",
        })
        self.anonymizer.anonymize_partner(partner, mode="anonymize")
        partner.invalidate_recordset()
        self.assertNotEqual(partner.name, "Alice Dupont")
        self.assertFalse(partner.email)
        self.assertFalse(partner.phone)
        self.assertFalse(partner.comment)
        # A log should have been created
        log = self.env["abrmd.rgpd.access.log"].search([
            ("log_type", "=", "anonymization"),
            ("res_id", "=", partner.id),
        ], limit=1)
        self.assertTrue(log)

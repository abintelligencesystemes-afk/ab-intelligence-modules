# -*- coding: utf-8 -*-
from odoo.tests import common, tagged


@tagged("post_install", "-at_install", "abrmd_rgpd")
class TestConsent(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.registre = cls.env["abrmd.rgpd.registre"].create({
            "name": "Test traitement",
            "code": "TST-001",
            "controller_name": "Test SAS",
            "controller_email": "controller@test.local",
            "purpose": "Test unitaire",
            "legal_basis": "consent",
            "data_subjects": "Testeurs",
            "data_categories": "Email",
            "retention_days": 30,
        })

    def test_consent_creation(self):
        c = self.env["abrmd.rgpd.consent"].create({
            "subject_email": "alice@test.local",
            "registre_id": self.registre.id,
            "purpose": "Newsletter",
            "capture_method": "web_form",
        })
        self.assertEqual(c.state, "given")
        self.assertTrue(c.subject_hash)
        self.assertEqual(len(c.subject_hash), 64)  # SHA-256 hex

    def test_consent_hash_stability(self):
        c1 = self.env["abrmd.rgpd.consent"].create({
            "subject_email": "Alice@Test.Local",
            "registre_id": self.registre.id,
            "purpose": "Newsletter",
            "capture_method": "web_form",
        })
        c2 = self.env["abrmd.rgpd.consent"].create({
            "subject_email": "alice@test.local",
            "registre_id": self.registre.id,
            "purpose": "Marketing",
            "capture_method": "web_form",
        })
        # Lowercase normalization → same hash
        self.assertEqual(c1.subject_hash, c2.subject_hash)

    def test_consent_withdraw(self):
        c = self.env["abrmd.rgpd.consent"].create({
            "subject_email": "bob@test.local",
            "registre_id": self.registre.id,
            "purpose": "Newsletter",
            "capture_method": "web_form",
        })
        c.action_withdraw()
        self.assertEqual(c.state, "withdrawn")
        self.assertTrue(c.withdrawal_date)

    def test_consent_renew_creates_new(self):
        c = self.env["abrmd.rgpd.consent"].create({
            "subject_email": "carol@test.local",
            "registre_id": self.registre.id,
            "purpose": "Newsletter",
            "capture_method": "web_form",
        })
        c.action_withdraw()
        action = c.action_renew()
        new_id = action["res_id"]
        new = self.env["abrmd.rgpd.consent"].browse(new_id)
        self.assertEqual(new.state, "given")
        self.assertEqual(c.state, "withdrawn")  # original unchanged

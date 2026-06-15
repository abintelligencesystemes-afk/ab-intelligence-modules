# -*- coding: utf-8 -*-
"""
Tests pour le matching signatures fournisseurs.
"""
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "abrmd_ai_achats")
class TestSignatureMatcher(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Partner = cls.env["res.partner"]
        cls.Sig = cls.env["abrmd.ai.supplier.signature"]
        cls.ingram = cls.Partner.create({
            "name": "Test Ingram Micro",
            "supplier_rank": 1,
            "vat": "FR42329257490",
            "company_type": "company",
        })
        cls.brossette = cls.Partner.create({
            "name": "Test Brossette",
            "supplier_rank": 1,
            "vat": "FR82542052485",
            "company_type": "company",
        })

    def test_match_ingram_via_vat(self):
        self.Sig.create({
            "partner_id": self.ingram.id,
            "signature_keywords": "Ingram,Micro,distribution",
            "vat_pattern": "FR42329257490",
            "confidence": 0.9,
        })
        text = "Facture INGRAM MICRO FRANCE - VAT FR42329257490 - distribution IT"
        partner, sig, score = self.Sig.match(text)
        self.assertEqual(partner, self.ingram)
        self.assertIsNotNone(sig)
        self.assertGreater(score, 0.8)

    def test_no_match_below_threshold(self):
        self.Sig.create({
            "partner_id": self.ingram.id,
            "signature_keywords": "X-rare-1,X-rare-2,X-rare-3,X-rare-4,X-rare-5",
            "confidence": 0.5,
        })
        text = "Une facture random sans aucun mot-clé"
        partner, sig, score = self.Sig.match(text, threshold=0.5)
        self.assertIsNone(partner if not partner else partner)
        self.assertLess(score, 0.5)

    def test_learn_increments_occurrences(self):
        sig1 = self.Sig.learn_or_update(
            partner_id=self.brossette.id,
            raw_text="Brossette FR82542052485 plomberie BTP",
            vat="FR82542052485",
        )
        self.assertEqual(sig1.occurrences, 1)
        sig2 = self.Sig.learn_or_update(
            partner_id=self.brossette.id,
            raw_text="Brossette FR82542052485 nouvelle facture",
            vat="FR82542052485",
        )
        self.assertEqual(sig2.id, sig1.id)
        self.assertEqual(sig2.occurrences, 2)
        self.assertGreater(sig2.confidence, sig1.confidence)

    def test_auto_extract_keywords(self):
        kws = self.Sig._auto_extract_keywords(
            "INGRAM Micro France distribution informatique professionnelle",
            vat="FR42329257490",
        )
        self.assertIn("FR42329257490", kws)
        self.assertIn("INGRAM", kws)

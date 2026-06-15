# -*- coding: utf-8 -*-
"""
Tests pour le matching produits.
"""
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "abrmd_ai_achats")
class TestProductMatcher(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Partner = cls.env["res.partner"]
        cls.Product = cls.env["product.product"]
        cls.Match = cls.env["abrmd.ai.product.match"]

        cls.ingram = cls.Partner.create({
            "name": "Test Ingram Micro",
            "supplier_rank": 1,
            "company_type": "company",
        })
        cls.mbp = cls.Product.create({
            "name": "MacBook Pro 14 M4",
            "default_code": "MBP14-M4",
            "type": "consu",
        })

    def test_exact_ref_match(self):
        self.Match.create({
            "partner_id": self.ingram.id,
            "supplier_ref": "MBP14-M4",
            "supplier_name": "MacBook Pro 14 M4",
            "product_id": self.mbp.id,
            "confidence": 0.95,
        })
        prod, rec, score = self.Match.match_line(
            partner_id=self.ingram.id,
            supplier_ref="MBP14-M4",
        )
        self.assertEqual(prod, self.mbp)
        self.assertEqual(score, 1.0)

    def test_no_match_unknown_ref(self):
        prod, rec, score = self.Match.match_line(
            partner_id=self.ingram.id,
            supplier_ref="UNKNOWN-REF",
            supplier_name="Random thing",
        )
        self.assertFalse(prod)
        self.assertEqual(score, 0.0)

    def test_learn_creates_then_updates(self):
        rec1 = self.Match.learn(
            partner_id=self.ingram.id,
            product_id=self.mbp.id,
            supplier_ref="MBP14-M4",
            supplier_name="MacBook Pro 14 M4 Space Black",
            unit_price=2000.0,
        )
        self.assertEqual(rec1.occurrences, 1)
        self.assertEqual(rec1.unit_price_avg, 2000.0)

        rec2 = self.Match.learn(
            partner_id=self.ingram.id,
            product_id=self.mbp.id,
            supplier_ref="MBP14-M4",
            supplier_name="MacBook Pro 14 M4",
            unit_price=2100.0,
        )
        self.assertEqual(rec2.id, rec1.id)
        self.assertEqual(rec2.occurrences, 2)
        self.assertAlmostEqual(rec2.unit_price_avg, 2050.0, places=2)
        self.assertEqual(rec2.last_unit_price, 2100.0)

    def test_fuzzy_name_match(self):
        self.Match.create({
            "partner_id": self.ingram.id,
            "supplier_ref": "REF-A",
            "supplier_name": "MacBook Pro 14 M4 Space Black",
            "product_id": self.mbp.id,
            "confidence": 0.9,
        })
        # Threshold faible exigé car Jaccard sur 4 tokens vs 5 → 4/5 = 0.8
        prod, rec, score = self.Match.match_line(
            partner_id=self.ingram.id,
            supplier_name="MacBook Pro 14 M4 Space Black",
            threshold=0.8,
        )
        self.assertEqual(prod, self.mbp)
        self.assertGreaterEqual(score, 0.8)

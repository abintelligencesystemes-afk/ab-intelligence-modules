# -*- coding: utf-8 -*-
"""
Tests pipeline learning (cache hit, sans appel Worker).
"""
import json
import base64
import hashlib

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "abrmd_ai_achats")
class TestLearningPipeline(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Scan = self.env["abrmd.ai.achat.scan"]
        self.Cache = self.env["abrmd.ai.invoice.cache"]

    def test_cache_hit_no_worker_call(self):
        """Si un hash existe en cache, le pipeline ne doit pas appeler le Worker."""
        sample = b"PDF-FAKE-DATA-12345"
        b64 = base64.b64encode(sample)
        h = hashlib.sha256(sample).hexdigest()

        cached_json = json.dumps({
            "supplier_name": "Cached Supplier",
            "invoice_date": "2026-05-20",
            "invoice_number": "INV-CACHED",
            "total_ttc": 100.0,
            "lines": [{"description": "Test", "quantity": 1, "unit_price": 100.0}],
        })
        self.Cache.store(
            file_hash=h,
            extracted_json=cached_json,
            cost_usd=0.05,
        )

        scan = self.Scan.create({
            "scanned_file": b64,
            "scanned_filename": "test.pdf",
            "scanned_mime_type": "application/pdf",
            "scan_type": "invoice",
        })
        self.Scan._run_ocr_pipeline(scan)

        self.assertEqual(scan.state, "cached")
        self.assertEqual(scan.source, "cache_hit")
        self.assertEqual(scan.cost_usd, 0.0)
        self.assertEqual(scan.fournisseur_detected, "Cached Supplier")
        self.assertEqual(scan.reference_detected, "INV-CACHED")

    def test_cache_hit_increments_count(self):
        sample = b"FAKE-PDF-22"
        b64 = base64.b64encode(sample)
        h = hashlib.sha256(sample).hexdigest()
        cached = self.Cache.store(
            file_hash=h,
            extracted_json=json.dumps({"supplier_name": "X", "invoice_date": "2026-05-20",
                                       "invoice_number": "X", "total_ttc": 1.0, "lines": []}),
        )
        self.assertEqual(cached.hit_count, 0)

        scan = self.Scan.create({
            "scanned_file": b64,
            "scanned_filename": "x.pdf",
            "scanned_mime_type": "application/pdf",
        })
        self.Scan._run_ocr_pipeline(scan)
        cached.invalidate_recordset()
        self.assertEqual(cached.hit_count, 1)

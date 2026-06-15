# -*- coding: utf-8 -*-
"""Tests Odoo (TransactionCase) — abrmd.grow.post."""
try:
    from odoo.tests.common import TransactionCase, tagged
except Exception:  # pragma: no cover
    TransactionCase = object

    def tagged(*args, **kwargs):
        def deco(cls):
            return cls
        return deco


@tagged("post_install", "-at_install")
class TestGrowPost(TransactionCase):
    def test_create_minimal_post(self):
        Post = self.env["abrmd.grow.post"]
        rec = Post.create({"title": "Test post", "canal": "linkedin"})
        self.assertTrue(rec)
        self.assertEqual(rec.state, "draft")
        self.assertFalse(rec.published)

    def test_state_transitions(self):
        Post = self.env["abrmd.grow.post"]
        rec = Post.create({"title": "FSM", "canal": "instagram"})
        rec.action_send_to_review()
        self.assertEqual(rec.state, "review")
        rec.scheduled_date = "2026-12-31"
        rec.action_schedule()
        self.assertEqual(rec.state, "scheduled")
        rec.action_mark_published()
        self.assertEqual(rec.state, "published")
        self.assertTrue(rec.published)

    def test_char_count(self):
        Post = self.env["abrmd.grow.post"]
        rec = Post.create({
            "title": "Char",
            "canal": "twitter",
            "content": "Hello world.",
        })
        self.assertEqual(rec.char_count, len("Hello world."))

    def test_build_ai_prompt_pure(self):
        Post = self.env["abrmd.grow.post"]
        prompt = Post.build_ai_prompt(canal="linkedin", angle="urgence livraison")
        self.assertIn("linkedin", prompt)
        self.assertIn("urgence livraison", prompt)
        self.assertIn("RMD Store", prompt)

    def test_cron_check_due_no_records(self):
        Post = self.env["abrmd.grow.post"]
        # Aucun post → 0 notif
        result = Post.cron_check_due()
        self.assertEqual(result, 0)

    def test_cron_check_due_kill_switch(self):
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("abrmd_grow_marketing.killed", "True")
        Post = self.env["abrmd.grow.post"]
        # Crée un post du jour
        from odoo import fields as ofields
        Post.create({
            "title": "Should be skipped",
            "canal": "linkedin",
            "scheduled_date": ofields.Date.today(),
            "state": "scheduled",
        })
        result = Post.cron_check_due()
        self.assertEqual(result, 0)  # kill switch actif
        ICP.set_param("abrmd_grow_marketing.killed", "False")

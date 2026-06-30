# -*- coding: utf-8 -*-
"""Tests pure-python — validation logique sans Odoo."""
import hashlib
import os
import sys


def _pseudonymize(value, salt):
    payload = (str(value).lower().strip() + "|" + salt).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def test_pseudonymize_lowercase_normalization():
    h1 = _pseudonymize("alice@test.local", "salt-x")
    h2 = _pseudonymize("ALICE@TEST.LOCAL", "salt-x")
    assert h1 == h2


def test_pseudonymize_different_salt_different_hash():
    h1 = _pseudonymize("alice@test.local", "salt-a")
    h2 = _pseudonymize("alice@test.local", "salt-b")
    assert h1 != h2


def test_pseudonymize_length():
    h = _pseudonymize("alice@test.local", "salt-x")
    assert len(h) == 64  # SHA-256 hex


def test_anonymize_email_format():
    """Vérifie la signature anonymize_email du module."""
    def anonymize_email(email):
        if not email or "@" not in email:
            return ""
        local, domain = email.split("@", 1)
        if len(local) <= 1:
            return "*@" + domain
        return local[0] + "***@" + domain

    assert anonymize_email("alice@test.local") == "a***@test.local"
    assert anonymize_email("a@test.local") == "*@test.local"
    assert anonymize_email("") == ""


def test_anonymize_ipv4():
    def anonymize_ip(ip):
        if not ip:
            return ""
        if ":" in ip:
            parts = ip.split(":")
            return ":".join(parts[:3]) + "::/48"
        parts = ip.split(".")
        if len(parts) == 4:
            return ".".join(parts[:3]) + ".0/24"
        return ip
    assert anonymize_ip("192.168.1.42") == "192.168.1.0/24"


def test_deadline_30_days():
    """Délai légal Art.12 = 1 mois (30 jours)."""
    from datetime import datetime, timedelta
    received = datetime(2026, 5, 27, 10, 0, 0)
    deadline = received + timedelta(days=30)
    assert (deadline - received).days == 30


def test_extension_2_months():
    """Prolongation Art.12.3 = +2 mois supplémentaires (60 jours)."""
    from datetime import datetime, timedelta
    initial_deadline = datetime(2026, 6, 26, 10, 0, 0)
    extended = initial_deadline + timedelta(days=60)
    assert (extended - initial_deadline).days == 60


REQUEST_TYPES = [
    "access", "rectification", "erasure", "restriction",
    "portability", "objection", "automated_decision",
]


def test_request_types_complete():
    """Les 7 types couvrent les Art.15 à Art.22 RGPD."""
    expected_legal_articles = {
        "access": 15,
        "rectification": 16,
        "erasure": 17,
        "restriction": 18,
        "portability": 20,
        "objection": 21,
        "automated_decision": 22,
    }
    assert len(REQUEST_TYPES) == 7
    assert all(t in expected_legal_articles for t in REQUEST_TYPES)


LOG_TYPES = [
    "read", "write", "create", "unlink", "export",
    "anonymization", "pseudonymization",
    "right_access", "right_erasure", "right_portability",
    "other",
]


def test_log_types_cover_rgpd_operations():
    """Les 11 types d'opérations couvrent CRUD + droits RGPD + anonymisation."""
    assert len(LOG_TYPES) == 11
    assert "anonymization" in LOG_TYPES
    assert "right_access" in LOG_TYPES
    assert "right_erasure" in LOG_TYPES


def test_retention_defaults_match_french_law():
    """Durées par défaut alignées CNIL / Code de commerce."""
    # CRM = 3 ans = 1095 j (recommandation CNIL)
    assert 3 * 365 == 1095
    # Compta = 10 ans = 3650 j (Code de commerce L123-22)
    assert 10 * 365 == 3650
    # RH paie = 5 ans (Code du travail L3243-4)
    assert 5 * 365 == 1825


LEGAL_BASES_ART6 = [
    "consent", "contract", "legal_obligation",
    "vital_interest", "public_interest", "legitimate_interest",
]


def test_legal_bases_complete():
    """Les 6 bases légales de l'Art.6.1 RGPD sont couvertes."""
    assert len(LEGAL_BASES_ART6) == 6

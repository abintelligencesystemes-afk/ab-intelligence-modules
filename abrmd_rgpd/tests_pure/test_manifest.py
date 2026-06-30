# -*- coding: utf-8 -*-
"""Tests pure-python (hors Odoo) — validation manifest + structure."""
import ast
import csv
import os
import xml.etree.ElementTree as ET
import pytest


MODULE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_manifest():
    with open(os.path.join(MODULE_DIR, "__manifest__.py"), encoding="utf-8") as f:
        return ast.literal_eval(f.read())


def test_manifest_loads():
    m = _load_manifest()
    assert m["name"]
    assert m["version"] == "19.0.0.2.0"
    assert m["license"] == "LGPL-3"
    assert m["application"] is True


def test_manifest_dependencies():
    m = _load_manifest()
    assert "base" in m["depends"]
    assert "mail" in m["depends"]


def test_required_files_exist():
    required = [
        "__init__.py",
        "hooks.py",
        "models/__init__.py",
        "models/abrmd_rgpd_registre.py",
        "models/abrmd_rgpd_consent.py",
        "models/abrmd_rgpd_request.py",
        "models/abrmd_rgpd_anonymizer.py",
        "models/abrmd_rgpd_access_log.py",
        "models/abrmd_rgpd_dashboard.py",
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/cron_data.xml",
        "data/default_registre_data.xml",
        "data/ir_actions_server.xml",
        "views/menu_views.xml",
        "views/registre_views.xml",
        "views/consent_views.xml",
        "views/request_views.xml",
        "views/access_log_views.xml",
        "views/dashboard_views.xml",
        "views/res_config_settings_views.xml",
        "README.md",
        "CHANGELOG.md",
        "LICENSE",
    ]
    for f in required:
        path = os.path.join(MODULE_DIR, f)
        assert os.path.exists(path), "Missing required file: %s" % f


def test_xml_files_parse():
    """Tous les XML du module doivent être bien formés."""
    for root, _, files in os.walk(MODULE_DIR):
        for f in files:
            if f.endswith(".xml"):
                path = os.path.join(root, f)
                try:
                    ET.parse(path)
                except ET.ParseError as exc:
                    pytest.fail("XML parse error in %s: %s" % (path, exc))


def test_security_csv_complete():
    """ir.model.access.csv doit lister tous les modèles non-abstract du module."""
    with open(os.path.join(MODULE_DIR, "security/ir.model.access.csv"), encoding="utf-8") as f:
        reader = csv.DictReader(f)
        models = {row["model_id:id"] for row in reader}
    expected = {
        "model_abrmd_rgpd_registre",
        "model_abrmd_rgpd_consent",
        "model_abrmd_rgpd_request",
        "model_abrmd_rgpd_access_log",
        "model_abrmd_rgpd_dashboard",
    }
    missing = expected - models
    assert not missing, "ir.model.access.csv missing entries for: %s" % missing


def test_no_secret_in_source():
    """Aucune clé API hardcodée dans le module (hors tests qui définissent le motif à chercher)."""
    suspect = "".join(["sk", "_", "live"]), "".join(["sk", "_", "test", "_"]), "OPENAI" + "_API_KEY=", "Bearer " + "ey"
    for root, _, files in os.walk(MODULE_DIR):
        # Skip cache dirs and the test file itself which references the patterns
        if "__pycache__" in root or ".pytest_cache" in root or "tests_pure" in root:
            continue
        for f in files:
            if not (f.endswith(".py") or f.endswith(".xml")):
                continue
            path = os.path.join(root, f)
            with open(path, encoding="utf-8", errors="ignore") as fh:
                content = fh.read()
            for s in suspect:
                assert s not in content, "Suspect secret pattern %r in %s" % (s, path)


def test_no_fk_to_res_users_in_consent():
    """Pour respecter le design RGPD du chatbot v0.1, le modèle consent NE DOIT PAS lier res.users."""
    with open(os.path.join(MODULE_DIR, "models/abrmd_rgpd_consent.py"), encoding="utf-8") as f:
        content = f.read()
    # Seul res.partner est autorisé (sujet réel)
    assert "res.users" not in content, "Consent ne doit pas lier res.users — RGPD principe minimisation"


def test_hooks_present():
    with open(os.path.join(MODULE_DIR, "hooks.py"), encoding="utf-8") as f:
        content = f.read()
    assert "_post_init_hook" in content
    assert "_uninstall_hook" in content
    assert "_safe_ping" in content


def test_pillars_models_present():
    """Les 5 modèles (+ AbstractModel anonymizer) implémentent les 6 piliers."""
    models_dir = os.path.join(MODULE_DIR, "models")
    expected_files = {
        "abrmd_rgpd_registre.py",     # Pilier 1
        "abrmd_rgpd_consent.py",      # Pilier 2
        "abrmd_rgpd_request.py",      # Pilier 3
        "abrmd_rgpd_anonymizer.py",   # Pilier 4
        "abrmd_rgpd_access_log.py",   # Pilier 5
        "abrmd_rgpd_dashboard.py",    # Pilier 6
    }
    found = set(os.listdir(models_dir))
    missing = expected_files - found
    assert not missing, "Pillars missing: %s" % missing

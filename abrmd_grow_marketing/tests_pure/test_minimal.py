"""Tests pure-python (sans Odoo) — abrmd_grow_marketing V0.2.

Lance avec : pytest tests_pure/ -v
ou : ./run_tests.sh
"""
import pathlib
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parent.parent


def test_manifest_parsable_and_valid():
    manifest_path = ROOT / "__manifest__.py"
    assert manifest_path.exists()
    content = manifest_path.read_text(encoding="utf-8")
    data = eval(content)
    assert isinstance(data, dict)
    for required in ("name", "version", "license", "author", "depends", "category"):
        assert required in data, f"manifest manque {required}"
    assert data["license"] == "LGPL-3"
    assert data["version"].startswith("19.0.0.2"), f"version doit être 19.0.0.2.x, got {data['version']}"
    for dep in ("base", "mail", "web", "product", "project", "sale"):
        assert dep in data["depends"], f"depends manque {dep}"
    # Hooks contrôle distant présents
    assert data.get("post_init_hook") == "post_init_hook"
    assert data.get("uninstall_hook") == "uninstall_hook"
    # Assets bundle déclaré
    assets = data.get("assets", {})
    assert "web.assets_backend" in assets
    # Nouvelles vues V0.2 incluses
    data_files = data.get("data", [])
    expected_views = [
        "views/abrmd_grow_idea_views.xml",
        "views/abrmd_grow_media_views.xml",
        "views/abrmd_grow_pattern_views.xml",
        "views/abrmd_grow_video_views.xml",
    ]
    for v in expected_views:
        assert v in data_files, f"manifest manque {v}"


def test_security_csv_exists_and_has_header():
    csv = ROOT / "security" / "ir.model.access.csv"
    assert csv.exists()
    body = csv.read_text(encoding="utf-8")
    first = body.splitlines()[0]
    assert "model_id:id" in first
    expected_models = [
        "model_abrmd_grow_post",
        "model_abrmd_grow_idea",
        "model_abrmd_grow_media",
        "model_abrmd_grow_pattern",
        "model_abrmd_grow_veille_video",
        "model_abrmd_grow_video",
        "model_abrmd_grow_tag",
        "model_abrmd_grow_generate_wizard",
        "model_abrmd_grow_video_wizard",
    ]
    for m in expected_models:
        assert m in body, f"security CSV manque {m}"


def test_no_api_key_in_clear_in_source():
    """Aucune clé API en clair commit."""
    suspicious = ["sk-proj-", "sk-ant-", "AIza", "AKIA", "ghp_", "xoxb-"]
    for py in ROOT.rglob("*.py"):
        if "tests" in str(py):
            continue
        content = py.read_text(encoding="utf-8", errors="ignore")
        for marker in suspicious:
            assert marker not in content, f"secret suspect dans {py}: {marker}"


def test_xml_files_parsable():
    xml_files = list(ROOT.rglob("*.xml"))
    assert xml_files, "Pas de fichier XML trouvé"
    for xml in xml_files:
        try:
            ET.parse(xml)
        except ET.ParseError as e:
            raise AssertionError(f"XML cassé : {xml} — {e}")


def test_required_files_present():
    expected = [
        "__init__.py",
        "__manifest__.py",
        "hooks.py",
        "README.md",
        "CHANGELOG.md",
        "LICENSE.txt",
        "models/__init__.py",
        "models/abrmd_grow_post.py",
        "models/abrmd_grow_idea.py",
        "models/abrmd_grow_media.py",
        "models/abrmd_grow_pattern.py",
        "models/abrmd_grow_veille_video.py",
        "models/abrmd_grow_video.py",
        "models/abrmd_grow_video_pipeline.py",
        "models/abrmd_grow_proposer.py",
        "models/abrmd_grow_telemetry.py",
        "models/product_template.py",
        "models/project_task.py",
        "models/res_config_settings.py",
        "wizard/__init__.py",
        "wizard/abrmd_grow_generate_wizard.py",
        "wizard/abrmd_grow_video_wizard.py",
        "wizard/abrmd_grow_generate_wizard_views.xml",
        "views/abrmd_grow_post_views.xml",
        "views/abrmd_grow_idea_views.xml",
        "views/abrmd_grow_media_views.xml",
        "views/abrmd_grow_pattern_views.xml",
        "views/abrmd_grow_video_views.xml",
        "views/product_template_views.xml",
        "views/project_task_views.xml",
        "views/res_config_settings.xml",
        "data/cron.xml",
        "data/ir_config_parameter.xml",
        "security/ir.model.access.csv",
        "static/description/icon.png",
        "static/description/banner.png",
        "static/description/index.html",
        "static/src/js/grow_post_preview.js",
        "static/src/xml/grow_post_preview.xml",
        "static/src/scss/grow_post.scss",
        "i18n/fr.po",
        "i18n/en.po",
        "tests/__init__.py",
        "tests/test_grow_post.py",
        "tests/test_telemetry.py",
    ]
    missing = [f for f in expected if not (ROOT / f).exists()]
    assert not missing, f"Fichiers manquants : {missing}"


def test_hooks_safe_ping_present():
    hooks = (ROOT / "hooks.py").read_text(encoding="utf-8")
    assert "post_init_hook" in hooks
    assert "uninstall_hook" in hooks
    assert "_safe_ping" in hooks
    assert "abrmd.grow.telemetry" in hooks


def test_build_ai_prompt_signature():
    """Le module expose bien la méthode build_ai_prompt (sans Odoo, on grep)."""
    src = (ROOT / "models" / "abrmd_grow_post.py").read_text(encoding="utf-8")
    assert "def build_ai_prompt" in src
    assert "canal" in src
    assert "angle" in src
    assert "objectif" in src, "V0.2 doit exposer objectif"
    assert "patterns" in src, "V0.2 doit exposer patterns"


def test_no_auto_publish_in_v02():
    """Règle dure V0.2 : aucune publication automatique sur les réseaux."""
    sources = [
        (ROOT / "models" / "abrmd_grow_post.py").read_text(encoding="utf-8"),
        (ROOT / "wizard" / "abrmd_grow_generate_wizard.py").read_text(encoding="utf-8"),
        (ROOT / "models" / "abrmd_grow_video.py").read_text(encoding="utf-8"),
    ]
    forbidden = [
        "api.linkedin.com",
        "graph.facebook.com",
        "api.twitter.com",
        "api.x.com",
        "graph.instagram.com",
        "open.tiktokapis.com",
    ]
    for src in sources:
        for endpoint in forbidden:
            assert endpoint not in src, f"V0.2 ne doit pas appeler {endpoint}"


def test_kill_switch_param_documented():
    """Le kill switch doit être documenté + initialisé."""
    icp = (ROOT / "data" / "ir_config_parameter.xml").read_text(encoding="utf-8")
    assert "abrmd_grow_marketing.killed" in icp
    manifest = (ROOT / "__manifest__.py").read_text(encoding="utf-8")
    assert "Kill switch" in manifest or "kill" in manifest.lower()


def test_canal_selection_complete():
    """Les 7 canaux sont définis (linkedin, instagram, facebook, twitter, youtube, threads, tiktok)."""
    src = (ROOT / "models" / "abrmd_grow_post.py").read_text(encoding="utf-8")
    for canal in ("linkedin", "instagram", "facebook", "twitter", "youtube", "threads", "tiktok"):
        assert canal in src, f"canal manquant : {canal}"


def test_cron_propose_daily_declared():
    """Le cron propose_daily est bien déclaré dans data/cron.xml."""
    cron = (ROOT / "data" / "cron.xml").read_text(encoding="utf-8")
    assert "cron_propose_daily_ideas" in cron
    assert "07:00:00" in cron, "doit tourner à 07h"


def test_cron_video_process_declared():
    """Le cron video process est bien déclaré."""
    cron = (ROOT / "data" / "cron.xml").read_text(encoding="utf-8")
    assert "cron_process_pending_videos" in cron


def test_char_limits_canals_defined():
    """Les limites de caractères par canal sont bien définies."""
    src = (ROOT / "models" / "abrmd_grow_post.py").read_text(encoding="utf-8")
    assert "CHAR_LIMITS" in src
    for canal in ("linkedin", "instagram", "twitter", "tiktok"):
        assert canal in src

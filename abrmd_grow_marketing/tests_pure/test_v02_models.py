"""Tests pure-python V0.2 — nouveaux modèles + pipeline vidéo.

Pas d'import Odoo : on lit les fichiers comme du texte et on vérifie
la présence des constructions clés. Pour les helpers pure-python
(parse_proposer_response, build_srt_from_text, build_ffmpeg_cmd),
on les charge dynamiquement via importlib en stubbant les imports Odoo.
"""
import importlib.util
import pathlib
import sys
import types

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _stub_odoo():
    """Stub minimaliste du namespace odoo pour permettre l'import des modèles."""
    if "odoo" in sys.modules:
        return sys.modules["odoo"]
    odoo = types.ModuleType("odoo")
    odoo.api = types.SimpleNamespace(
        model=lambda f: f, depends=lambda *args: (lambda f: f),
        ondelete=lambda *args, **kw: (lambda f: f),
    )

    class _Field:
        def __init__(self, *args, **kwargs):
            pass

    fields_mod = types.SimpleNamespace(
        Char=_Field, Text=_Field, Integer=_Field, Float=_Field, Boolean=_Field,
        Selection=_Field, Date=_Field, Datetime=_Field, Many2one=_Field,
        Many2many=_Field, One2many=_Field, Binary=_Field, Image=_Field,
    )
    odoo.fields = fields_mod

    class _Meta(type):
        def __new__(mcs, name, bases, ns):
            return super().__new__(mcs, name, bases, ns)

    class _BaseModel(metaclass=_Meta):
        _name = ""
        _description = ""

        def __init_subclass__(cls, **kw):
            super().__init_subclass__(**kw)

    odoo.models = types.SimpleNamespace(
        Model=_BaseModel, AbstractModel=_BaseModel, TransientModel=_BaseModel,
    )
    odoo.exceptions = types.SimpleNamespace(UserError=Exception)
    odoo._ = lambda s, *a, **kw: s
    sys.modules["odoo"] = odoo
    sys.modules["odoo.api"] = odoo.api
    sys.modules["odoo.fields"] = odoo.fields
    sys.modules["odoo.models"] = odoo.models
    sys.modules["odoo.exceptions"] = odoo.exceptions
    return odoo


def _load_module(name, relative_path):
    """Charge un module Python en stubant Odoo."""
    _stub_odoo()
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_pipeline_estimate_cost():
    """estimate_cost est pure-python et raisonnable."""
    pipeline_mod = _load_module(
        "vp", "models/abrmd_grow_video_pipeline.py"
    )
    Pipeline = pipeline_mod.AbrmdGrowVideoPipeline
    # Coût pour un script court avec openai_tts + whisper sur 30s
    cost = Pipeline.estimate_cost("Hello world.", "openai_tts", 30.0)
    assert isinstance(cost, float)
    assert 0.0 < cost < 0.10, f"coût hors zone low-cost : {cost}"
    # Coût ElevenLabs doit être plus élevé
    cost_eleven = Pipeline.estimate_cost("Hello world.", "elevenlabs", 30.0)
    assert cost_eleven > cost
    # Coût sans script doit être quasi nul
    cost_nul = Pipeline.estimate_cost("", "openai_tts", 0.0)
    assert cost_nul < 0.02


def test_pipeline_build_srt_from_text():
    """build_srt_from_text génère un SRT valide."""
    pipeline_mod = _load_module(
        "vp2", "models/abrmd_grow_video_pipeline.py"
    )
    Pipeline = pipeline_mod.AbrmdGrowVideoPipeline
    srt = Pipeline.build_srt_from_text(
        "Mac mini M4 reconditionné garanti deux ans", duration_s=10.0
    )
    assert "1\n" in srt or srt.startswith("1")
    assert "00:00:00" in srt
    assert "-->" in srt
    assert "Mac mini" in srt
    # SRT vide pour texte vide
    assert Pipeline.build_srt_from_text("", 10.0) == ""


def test_pipeline_build_ffmpeg_cmd():
    """build_ffmpeg_cmd retourne une liste d'arguments cohérente."""
    pipeline_mod = _load_module(
        "vp3", "models/abrmd_grow_video_pipeline.py"
    )
    Pipeline = pipeline_mod.AbrmdGrowVideoPipeline
    cmd = Pipeline.build_ffmpeg_cmd(
        image_paths=["/tmp/a.jpg", "/tmp/b.jpg"],
        audio_path="",
        srt_path="",
        output_path="/tmp/out.mp4",
        width=1080, height=1920, max_duration=30,
        burn_subtitles=False,
    )
    assert cmd[0] == "ffmpeg"
    assert "/tmp/out.mp4" in cmd
    assert "-c:v" in cmd
    # Sans image, retourne []
    assert Pipeline.build_ffmpeg_cmd([], "", "", "/tmp/out.mp4") == []


def test_pipeline_fmt_srt_time():
    """_fmt_srt_time formate correctement (HH:MM:SS,mmm)."""
    pipeline_mod = _load_module(
        "vp4", "models/abrmd_grow_video_pipeline.py"
    )
    fmt = pipeline_mod._fmt_srt_time
    assert fmt(0.0) == "00:00:00,000"
    assert fmt(1.5) == "00:00:01,500"
    assert fmt(65.0) == "00:01:05,000"
    assert fmt(-3.0) == "00:00:00,000"  # clamp à 0


def test_media_guess_mimetype():
    """guess_mimetype reconnaît les principaux types."""
    media_mod = _load_module("media", "models/abrmd_grow_media.py")
    M = media_mod.AbrmdGrowMedia
    assert M.guess_mimetype("photo.jpg") == "image/jpeg"
    assert M.guess_mimetype("PHOTO.JPEG") == "image/jpeg"
    assert M.guess_mimetype("logo.png") == "image/png"
    assert M.guess_mimetype("clip.mp4") == "video/mp4"
    assert M.guess_mimetype("clip.MOV") == "video/quicktime"
    assert M.guess_mimetype("unknown.xyz") == "application/octet-stream"
    assert M.guess_mimetype("") == ""


def test_wizard_parse_proposals():
    """parse_proposals split correctement sur ---PROP---."""
    wizard_mod = _load_module(
        "w", "wizard/abrmd_grow_generate_wizard.py"
    )
    W = wizard_mod.AbrmdGrowGenerateWizard
    raw = "Prop A\n---PROP---\nProp B\n---PROP---\nProp C"
    props = W.parse_proposals(raw, n=3)
    assert len(props) == 3
    assert "Prop A" in props[0]
    assert "Prop B" in props[1]
    assert "Prop C" in props[2]
    # Si moins de propositions que demandé, duplique
    raw2 = "Prop unique"
    props2 = W.parse_proposals(raw2, n=3)
    assert len(props2) == 3
    # Vide
    assert W.parse_proposals("", n=3) == []


def test_proposer_parse_response_json():
    """parse_proposer_response gère JSON bien formé et entouré de markdown."""
    src = (ROOT / "models" / "abrmd_grow_proposer.py").read_text(encoding="utf-8")
    # On vérifie juste la présence des éléments attendus dans le code
    # (parser stricte non testé ici, car nécessite env Odoo complet)
    assert "def parse_proposer_response" in src
    assert "json.loads" in src
    assert "canal_suggested" in src


def test_video_model_has_workflow_states():
    src = (ROOT / "models" / "abrmd_grow_video.py").read_text(encoding="utf-8")
    for state in ("draft", "generating", "ready", "failed"):
        assert state in src, f"state vidéo manquant : {state}"


def test_video_pipeline_calls_openai_endpoints():
    src = (ROOT / "models" / "abrmd_grow_video_pipeline.py").read_text(encoding="utf-8")
    assert "audio/speech" in src, "doit appeler l'endpoint OpenAI TTS"
    assert "audio/transcriptions" in src, "doit appeler l'endpoint OpenAI Whisper"
    assert "subprocess" in src, "doit utiliser subprocess pour FFmpeg"


def test_idea_workflow_states():
    src = (ROOT / "models" / "abrmd_grow_idea.py").read_text(encoding="utf-8")
    for state in ("proposed", "approved", "rejected", "used"):
        assert state in src, f"state idée manquant : {state}"


def test_pattern_score_recency():
    src = (ROOT / "models" / "abrmd_grow_pattern.py").read_text(encoding="utf-8")
    assert "composite_score" in src
    assert "recency_weight" in src


def test_veille_unique_constraint():
    src = (ROOT / "models" / "abrmd_grow_veille_video.py").read_text(encoding="utf-8")
    assert "_sql_constraints" in src
    assert "unique(platform, external_id)" in src


def test_proposer_has_cron_method():
    src = (ROOT / "models" / "abrmd_grow_proposer.py").read_text(encoding="utf-8")
    assert "def cron_propose_daily_ideas" in src
    assert "_fallback_ideas" in src


def test_low_cost_target_documented():
    """Le manifest doit mentionner explicitement le low-cost vidéo."""
    manifest = (ROOT / "__manifest__.py").read_text(encoding="utf-8")
    assert "low-cost" in manifest.lower() or "FFmpeg" in manifest


def test_charlimits_values_reasonable():
    """Vérifie quelques limites de caractères codées (sanity check)."""
    pipeline_mod = _load_module("pmod", "models/abrmd_grow_post.py")
    assert pipeline_mod.CHAR_LIMITS["twitter"] == 280
    assert pipeline_mod.CHAR_LIMITS["linkedin"] == 3000
    assert pipeline_mod.CHAR_LIMITS["instagram"] == 2200

# -*- coding: utf-8 -*-
"""Wizard de génération de post Grow Marketing — V0.2 OpenAI live.

Flux :
1. Anthony renseigne canal / angle / objectif (et éventuellement idea_id /
   pattern_ids / product_id ou task_id).
2. action_generate_preview() construit un prompt structuré et appelle
   OpenAI (gpt-4o-mini par défaut, gpt-4o si demandé), pour obtenir 3
   propositions de post.
3. Anthony choisit une proposition → action_create_post() crée le
   abrmd.grow.post en draft avec prompt + réponse stockés en audit.

Si la clé OpenAI n'est pas configurée, le wizard tombe sur un stub
explicite (utile en dev / staging).
"""
import json
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

try:
    import urllib.request as _urlreq
    import urllib.error as _urlerr
except Exception:  # pragma: no cover
    _urlreq = None
    _urlerr = None

_logger = logging.getLogger(__name__)

CANAL_SELECTION = [
    ("linkedin", "LinkedIn"),
    ("instagram", "Instagram"),
    ("facebook", "Facebook"),
    ("twitter", "X / Twitter"),
    ("youtube", "YouTube"),
    ("threads", "Threads"),
    ("tiktok", "TikTok"),
]

OPENAI_ENDPOINT = "https://api.openai.com/v1/chat/completions"
SYSTEM_PROMPT_V15 = (
    "Tu es Anthony Growth Agent, copywriter B2B/B2C suisse pour le studio "
    "AB Intelligence Systèmes et le e-commerce RMD Store (Apple reconditionné). "
    "Tu écris en français suisse-neutre, ton direct, percutant, peu d'emojis. "
    "Tes posts ont un hook fort dans les 3 premières secondes, "
    "un développement court, un CTA clair. Tu adaptes le format au canal."
)


class AbrmdGrowGenerateWizard(models.TransientModel):
    _name = "abrmd.grow.generate.wizard"
    _description = "Wizard — Générer un post via Anthony Growth Agent"

    source_model = fields.Char(string="Modèle source")
    source_res_id = fields.Integer(string="ID source")
    source_post_id = fields.Many2one(
        "abrmd.grow.post",
        string="Post source (régénération)",
        ondelete="set null",
    )
    product_id = fields.Many2one("product.template", string="Produit lié")
    task_id = fields.Many2one("project.task", string="Tâche liée")
    project_id = fields.Many2one("project.project", string="Projet lié")
    idea_id = fields.Many2one(
        "abrmd.grow.idea",
        string="Idée de départ",
    )
    pattern_ids = fields.Many2many(
        "abrmd.grow.pattern",
        relation="abrmd_grow_wizard_pattern_rel",
        column1="wizard_id",
        column2="pattern_id",
        string="Patterns à appliquer",
    )
    canal = fields.Selection(
        selection=CANAL_SELECTION,
        string="Canal",
        required=True,
        default="linkedin",
    )
    angle = fields.Char(
        string="Angle / Hook (optionnel)",
        help="Ex. 'mettre l'accent sur la rapidité de livraison Suisse'.",
    )
    objectif = fields.Selection(
        selection=[
            ("lead", "Lead / Conversion"),
            ("awareness", "Notoriété"),
            ("sales", "Ventes"),
            ("engagement", "Engagement"),
        ],
        string="Objectif",
        default="lead",
    )
    scheduled_date = fields.Date(string="Date de publication prévue")
    model_override = fields.Selection(
        selection=[
            ("gpt-4o-mini", "gpt-4o-mini (rapide, moins cher)"),
            ("gpt-4o", "gpt-4o (qualité max)"),
        ],
        string="Modèle GPT (override)",
        help="Si vide, utilise ir.config_parameter abrmd_grow_marketing.openai_model.",
    )
    n_proposals = fields.Integer(string="Nb propositions", default=3)

    prompt_preview = fields.Text(string="Prompt généré (lecture seule)", readonly=True)
    proposal_1 = fields.Text(string="Proposition 1")
    proposal_2 = fields.Text(string="Proposition 2")
    proposal_3 = fields.Text(string="Proposition 3")
    chosen = fields.Selection(
        selection=[("1", "1"), ("2", "2"), ("3", "3")],
        string="Proposition choisie",
        default="1",
    )
    ai_model_used = fields.Char(string="Modèle IA utilisé", readonly=True)
    ai_response_raw = fields.Text(string="Réponse brute API", readonly=True)
    state = fields.Selection(
        selection=[
            ("input", "Saisie"),
            ("preview", "Prévisualisation"),
            ("error", "Erreur"),
        ],
        default="input",
    )
    error_message = fields.Text(string="Message d'erreur", readonly=True)

    # ------------------------------------------------------------------
    # Logique
    # ------------------------------------------------------------------
    def _resolve_source_record(self):
        self.ensure_one()
        if self.product_id:
            return self.product_id
        if self.task_id:
            return self.task_id
        if self.source_model and self.source_res_id:
            return self.env[self.source_model].browse(self.source_res_id)
        return None

    def _get_openai_config(self):
        ICP = self.env["ir.config_parameter"].sudo()
        api_key = ICP.get_param("openai.api_key", default="").strip()
        default_model = ICP.get_param(
            "abrmd_grow_marketing.openai_model", default="gpt-4o-mini"
        )
        model = self.model_override or default_model
        return api_key, model

    def action_generate_preview(self):
        """Build le prompt et appelle OpenAI pour générer N propositions."""
        self.ensure_one()
        source = self._resolve_source_record()
        Post = self.env["abrmd.grow.post"]
        prompt = Post.build_ai_prompt(
            source_record=source,
            canal=self.canal,
            angle=self.angle,
            objectif=self.objectif,
            idea=self.idea_id or None,
            patterns=self.pattern_ids or None,
        )
        self.prompt_preview = prompt

        api_key, model = self._get_openai_config()
        if not api_key:
            # Stub explicite
            stub_text = (
                "[STUB V0.2 — pas de clé OpenAI configurée]\n\n"
                "Configure-la dans Configuration → Paramètres généraux → "
                "AB Intelligence Grow Marketing → Clé API OpenAI.\n\n"
                "--- Prompt utilisé ---\n" + prompt
            )
            self.proposal_1 = stub_text
            self.proposal_2 = (stub_text + "\n\n[Variante 2]")
            self.proposal_3 = (stub_text + "\n\n[Variante 3]")
            self.ai_model_used = "stub-no-key"
            self.state = "preview"
            return self._reopen()

        try:
            n = max(1, min(5, self.n_proposals or 3))
            proposals, raw = self._call_openai(prompt, model, n)
            for i, prop in enumerate(proposals[:3]):
                setattr(self, f"proposal_{i+1}", prop)
            self.ai_model_used = model
            self.ai_response_raw = raw[:8000]
            self.state = "preview"
        except Exception as exc:  # noqa: BLE001
            _logger.warning("[abrmd_grow_marketing] OpenAI call failed: %s", exc)
            self.state = "error"
            self.error_message = (
                "Échec génération IA : %s\n\n"
                "Vérifie la clé API OpenAI, la connectivité Internet et le quota."
            ) % exc
        return self._reopen()

    def _reopen(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    @api.model
    def _build_openai_payload(self, prompt, model, n):
        """Construit le payload pour l'API Chat Completions OpenAI.

        Pure-python, testable.
        """
        return {
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT_V15},
                {"role": "user", "content": prompt + (
                    f"\n\nRetourne exactement {n} propositions distinctes, "
                    f"séparées par la ligne `---PROP---`."
                )},
            ],
            "temperature": 0.85,
            "max_tokens": 1500,
        }

    def _call_openai(self, prompt, model, n):
        """Appel HTTP POST réel à api.openai.com/v1/chat/completions.

        Retourne (proposals: list[str], raw_response: str).
        """
        api_key, _model_default = self._get_openai_config()
        if not api_key:
            raise UserError(_("Clé OpenAI absente."))
        if _urlreq is None:
            raise UserError(_("urllib indisponible côté hébergeur."))
        payload = self._build_openai_payload(prompt, model, n)
        body = json.dumps(payload).encode("utf-8")
        req = _urlreq.Request(
            OPENAI_ENDPOINT,
            data=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "abrmd_grow_marketing/19.0.0.2.0",
            },
            method="POST",
        )
        with _urlreq.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8") or "{}"
            data = json.loads(raw)
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        # Split sur ---PROP---
        proposals = [p.strip() for p in content.split("---PROP---") if p.strip()]
        if len(proposals) < n:
            # Fallback : duplique si l'IA n'a pas suivi le format
            while len(proposals) < n:
                proposals.append(content.strip())
        return proposals, raw

    @staticmethod
    def parse_proposals(content, n=3):
        """Pure-python helper — split d'une réponse OpenAI brute en N propositions."""
        if not content:
            return []
        proposals = [p.strip() for p in content.split("---PROP---") if p.strip()]
        if len(proposals) < n:
            while len(proposals) < n:
                proposals.append(content.strip())
        return proposals[:n]

    def action_create_post(self):
        """Crée le abrmd.grow.post à partir de la proposition choisie."""
        self.ensure_one()
        idx = self.chosen or "1"
        content = getattr(self, f"proposal_{idx}") or ""
        if not content:
            raise UserError(_("Proposition vide. Régénère ou édite avant de créer."))
        source = self._resolve_source_record()
        title_base = (
            self.idea_id.name if self.idea_id
            else (source.display_name if source else _("Nouveau post"))
        )
        title = _("[Grow] %s") % title_base
        Post = self.env["abrmd.grow.post"]
        post = Post.create({
            "title": title[:255],
            "content": content,
            "canal": self.canal,
            "scheduled_date": self.scheduled_date,
            "product_id": self.product_id.id if self.product_id else False,
            "task_id": self.task_id.id if self.task_id else False,
            "project_id": self.project_id.id if self.project_id else False,
            "idea_id": self.idea_id.id if self.idea_id else False,
            "pattern_ids": [(6, 0, self.pattern_ids.ids)] if self.pattern_ids else False,
            "state": "review",
            "generated_by_ai": True,
            "ai_prompt": self.prompt_preview,
            "ai_model": self.ai_model_used,
            "ai_response_raw": self.ai_response_raw,
            "ai_objectif": self.objectif,
        })
        # Si l'idée existait, marque-la comme utilisée
        if self.idea_id:
            self.idea_id.action_mark_used()
        return {
            "type": "ir.actions.act_window",
            "name": _("Post Grow"),
            "res_model": "abrmd.grow.post",
            "res_id": post.id,
            "view_mode": "form",
            "target": "current",
        }

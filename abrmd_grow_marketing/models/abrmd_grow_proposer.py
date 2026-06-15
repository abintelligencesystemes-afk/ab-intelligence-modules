# -*- coding: utf-8 -*-
"""Modèle abstrait abrmd.grow.proposer — orchestrateur des idées du jour.

Cron quotidien 07h UTC :
1. Lit les top patterns actifs (composite_score desc, top 5).
2. Choisit un produit RMD random ou une tâche AB Intelligence en cours.
3. Appelle OpenAI (gpt-4o-mini) pour générer 3 idées de posts contextualisées.
4. Crée 3 abrmd.grow.idea en state proposed (created_by_cron=True).
5. Envoie un mail récap à Anthony (contact@rmdsto.re).

Tout est isolé dans un AbstractModel pour pouvoir tester unitairement.
"""
import json
import logging
import random

from odoo import _, api, fields, models

try:
    import urllib.request as _urlreq
except Exception:  # pragma: no cover
    _urlreq = None

_logger = logging.getLogger(__name__)

PROPOSER_SYSTEM_PROMPT = (
    "Tu es Anthony Growth Agent. À partir d'un produit ou d'une tâche-projet "
    "RMD Store / AB Intelligence Systèmes et de patterns marketing dominants "
    "récents, propose exactement 3 idées de posts (canaux multiples) sous "
    "forme de JSON strict : "
    '[{"titre": "...", "description": "...", "canal_suggested": "linkedin"}, ...]. '
    "Ne renvoie QUE le JSON, sans markdown ni commentaire."
)

OPENAI_ENDPOINT = "https://api.openai.com/v1/chat/completions"


class AbrmdGrowProposer(models.AbstractModel):
    _name = "abrmd.grow.proposer"
    _description = "Orchestrateur d'idées quotidiennes Grow Marketing"

    # ------------------------------------------------------------------
    # Helpers pure-python (testables)
    # ------------------------------------------------------------------
    @api.model
    def build_proposer_prompt(self, source_label, source_desc, patterns_summary):
        """Construit le prompt textuel pour l'API OpenAI.

        Pure-python : pas de side-effect.
        """
        parts = [
            "Source : " + (source_label or "(générique)"),
        ]
        if source_desc:
            parts.append("Détails source : " + str(source_desc)[:400])
        if patterns_summary:
            parts.append("Patterns dominants récents :")
            for p in patterns_summary:
                parts.append(
                    f"- {p.get('name')} [{p.get('platform')}/{p.get('pattern_type')}] "
                    f"score={p.get('score'):.2f}"
                )
        parts.append(
            "Retourne 3 idées au format JSON strict comme indiqué dans le system prompt."
        )
        return "\n".join(parts)

    @api.model
    def parse_proposer_response(self, raw):
        """Pure-python : parse une réponse JSON LLM, robuste aux entourages markdown."""
        if not raw:
            return []
        # Strip markdown fences si présentes
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            # ```json ... ``` → garder le milieu
            lines = cleaned.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            cleaned = "\n".join(lines).strip()
        try:
            data = json.loads(cleaned)
        except Exception:
            return []
        if not isinstance(data, list):
            return []
        out = []
        for item in data:
            if not isinstance(item, dict):
                continue
            title = item.get("titre") or item.get("title") or ""
            desc = item.get("description") or ""
            canal = item.get("canal_suggested") or item.get("canal") or "linkedin"
            if title:
                out.append({
                    "titre": title[:200],
                    "description": desc[:1000],
                    "canal_suggested": canal,
                })
        return out

    # ------------------------------------------------------------------
    # Pick source : produit ou tâche
    # ------------------------------------------------------------------
    @api.model
    def pick_source_record(self):
        """Retourne un product.template ou un project.task aléatoire.

        Priorité : produit en stock (si module stock disponible),
        sinon produit publié, sinon tâche en cours.
        """
        ProductTemplate = self.env["product.template"]
        # Tente d'abord les produits publiables / actifs
        candidates = ProductTemplate.search([("active", "=", True)], limit=200)
        if candidates:
            return random.choice(candidates)
        Task = self.env["project.task"]
        tasks = Task.search([
            ("state", "not in", ("done", "cancel", "1_done", "1_canceled")),
        ], limit=200) if "state" in Task._fields else Task.search([], limit=200)
        if tasks:
            return random.choice(tasks)
        return None

    @api.model
    def top_patterns(self, limit=5):
        """Top patterns actifs par composite_score."""
        Pattern = self.env["abrmd.grow.pattern"]
        return Pattern.search([("active", "=", True)], limit=limit, order="composite_score desc")

    # ------------------------------------------------------------------
    # Appel OpenAI
    # ------------------------------------------------------------------
    @api.model
    def _call_openai_json(self, prompt, timeout=30):
        ICP = self.env["ir.config_parameter"].sudo()
        api_key = ICP.get_param("openai.api_key", default="").strip()
        if not api_key:
            return None, "no_key"
        if _urlreq is None:
            return None, "no_urllib"
        model = ICP.get_param(
            "abrmd_grow_marketing.openai_model", default="gpt-4o-mini"
        )
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": PROPOSER_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.9,
            "max_tokens": 1200,
        }
        try:
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
            with _urlreq.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8") or "{}"
                data = json.loads(raw)
            return data.get("choices", [{}])[0].get("message", {}).get("content", ""), "ok"
        except Exception as exc:  # noqa: BLE001
            _logger.warning("[abrmd_grow_marketing] proposer OpenAI failed: %s", exc)
            return None, str(exc)

    # ------------------------------------------------------------------
    # Cron entry point
    # ------------------------------------------------------------------
    @api.model
    def cron_propose_daily_ideas(self):
        """Cron quotidien — propose 3 idées de posts.

        Retourne le nb d'idées créées (utile pour les tests).
        """
        ICP = self.env["ir.config_parameter"].sudo()
        if ICP.get_param("abrmd_grow_marketing.killed", default="False") == "True":
            _logger.info("[abrmd_grow_marketing] kill switch actif — proposer skip")
            return 0

        source = self.pick_source_record()
        patterns = self.top_patterns(limit=5)
        patterns_summary = [
            {
                "name": p.name,
                "platform": p.platform,
                "pattern_type": p.pattern_type,
                "score": p.composite_score or 0.0,
            } for p in patterns
        ]
        source_label = source.display_name if source else "(générique)"
        source_desc = ""
        if source is not None:
            source_desc = (
                getattr(source, "description_sale", None)
                or getattr(source, "description", None)
                or ""
            )
        prompt = self.build_proposer_prompt(source_label, source_desc, patterns_summary)

        raw, status = self._call_openai_json(prompt)
        if status != "ok" or not raw:
            # Fallback : crée 3 idées génériques basées sur la source
            _logger.info(
                "[abrmd_grow_marketing] proposer fallback (status=%s)", status
            )
            ideas_data = self._fallback_ideas(source_label, patterns_summary)
        else:
            ideas_data = self.parse_proposer_response(raw)
            if not ideas_data:
                ideas_data = self._fallback_ideas(source_label, patterns_summary)

        Idea = self.env["abrmd.grow.idea"]
        created = []
        product_id = source.id if source and source._name == "product.template" else False
        for item in ideas_data[:3]:
            idea = Idea.create({
                "name": item["titre"],
                "description": item["description"],
                "canal_suggested": item["canal_suggested"],
                "source": "cron_daily",
                "state": "proposed",
                "created_by_cron": True,
                "priority": "1",
                "product_id": product_id,
                "pattern_id": patterns[:1].id if patterns else False,
            })
            created.append(idea)

        # Mail récap (best-effort, non bloquant)
        try:
            self._send_recap_mail(created, source_label)
        except Exception as exc:  # noqa: BLE001
            _logger.warning(
                "[abrmd_grow_marketing] proposer mail récap échec : %s", exc
            )

        _logger.info(
            "[abrmd_grow_marketing] cron_propose_daily_ideas — %s idées créées",
            len(created),
        )
        return len(created)

    @api.model
    def _fallback_ideas(self, source_label, patterns_summary):
        """Idées générées sans LLM (utile en mode dev / pas de clé)."""
        canals = ["linkedin", "instagram", "tiktok"]
        out = []
        for i, canal in enumerate(canals):
            out.append({
                "titre": f"Idée #{i+1} — {source_label[:80]} [{canal}]",
                "description": (
                    f"Post {canal} centré sur {source_label}. "
                    f"Patterns suggérés : "
                    + (", ".join(p["name"] for p in patterns_summary[:3]) or "none")
                ),
                "canal_suggested": canal,
            })
        return out

    @api.model
    def _send_recap_mail(self, ideas, source_label):
        """Envoie un mail récap à contact@rmdsto.re."""
        if not ideas:
            return
        ICP = self.env["ir.config_parameter"].sudo()
        recipient = ICP.get_param(
            "abrmd_grow_marketing.recap_email", default="contact@rmdsto.re"
        )
        # On utilise mail.mail pour rester sobre (pas de template à déclarer).
        body_lines = [
            f"<p>Hello Anthony,</p>",
            f"<p>3 nouvelles idées de posts pour aujourd'hui "
            f"(source : <b>{source_label}</b>) :</p>",
            "<ul>",
        ]
        for idea in ideas:
            body_lines.append(
                f"<li><b>{idea.name}</b> "
                f"<i>({idea.canal_suggested})</i><br/>{idea.description or ''}</li>"
            )
        body_lines.append("</ul>")
        body_lines.append(
            "<p>Ouvre le module <i>Grow Marketing → Idées</i> pour les approuver "
            "et générer un brouillon de post.</p>"
        )
        body = "\n".join(body_lines)
        MailMail = self.env["mail.mail"]
        mail = MailMail.create({
            "subject": "[Grow Marketing] 3 idées de posts pour aujourd'hui",
            "body_html": body,
            "email_to": recipient,
            "auto_delete": True,
        })
        try:
            mail.send()
        except Exception as exc:  # noqa: BLE001
            _logger.warning(
                "[abrmd_grow_marketing] mail.send() échec : %s", exc
            )

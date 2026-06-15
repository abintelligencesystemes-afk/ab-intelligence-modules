# -*- coding: utf-8 -*-
"""Normalise name/email/phone sur res.partner pour recherche fuzzy."""
import re
import unicodedata

from odoo import api, fields, models

_NON_ALPHANUM_RE = re.compile(r"[^a-z0-9 ]+")
_WHITESPACE_RE = re.compile(r"\s+")


def _normalize(value):
    """Retourne une version 'searchable' du texte : minuscule, sans accent,
    sans ponctuation, espaces multiples réduits."""
    if not value:
        return ""
    # NFKD décompose les caractères accentués (é → e + ´)
    decomposed = unicodedata.normalize("NFKD", value)
    # Supprime les marques combinantes (accents)
    no_accent = "".join(
        ch for ch in decomposed if not unicodedata.combining(ch)
    )
    # Minuscule
    lowered = no_accent.lower()
    # Supprime ponctuation et caractères spéciaux
    cleaned = _NON_ALPHANUM_RE.sub(" ", lowered)
    # Compresse les espaces multiples
    return _WHITESPACE_RE.sub(" ", cleaned).strip()


class ResPartner(models.Model):
    _inherit = "res.partner"

    name_normalized = fields.Char(
        string="Nom normalisé (interne)",
        compute="_compute_name_normalized",
        store=True,
        index=True,
        help="Version recherchable du nom : sans accent, sans casse, "
             "sans ponctuation. Champ technique destiné à la recherche fuzzy.",
    )

    @api.depends("name", "email", "phone", "ref")
    def _compute_name_normalized(self):
        for partner in self:
            chunks = [
                _normalize(partner.name or ""),
                _normalize(partner.email or ""),
                _normalize(partner.phone or ""),
                _normalize(partner.ref or ""),
            ]
            partner.name_normalized = " ".join(c for c in chunks if c)

    @api.model
    def _name_search(
        self,
        name,
        domain=None,
        operator="ilike",
        limit=100,
        order=None,
    ):
        """Étend la recherche standard pour utiliser name_normalized si l'opérateur
        est `ilike` / `=ilike`. Permet de matcher 'francois' → 'François'."""
        domain = list(domain or [])
        if name and operator in ("ilike", "=ilike", "like", "=like"):
            normalized = _normalize(name)
            if normalized:
                # Recherche fuzzy via name_normalized en plus de la recherche
                # standard sur name. On combine avec OR.
                fuzzy_domain = [
                    "|",
                    "|",
                    ("name", operator, name),
                    ("name_normalized", operator, normalized),
                    ("ref", operator, name),
                ]
                domain = ["&"] + fuzzy_domain + domain if domain else fuzzy_domain
                return self._search(
                    domain, limit=limit, order=order or self._order
                )
        return super()._name_search(
            name, domain=domain, operator=operator, limit=limit, order=order
        )

# -*- coding: utf-8 -*-
"""
Référentiel de matching produits.

Pour chaque (fournisseur, supplier_ref/supplier_name) on associe un product.product
Odoo. Au scan d'une nouvelle facture, on consulte ce référentiel AVANT de tomber
dans le matching naïf Odoo (ilike sur product.name) — souvent inefficace.

Au fil du temps (mois 3+), 99 % des lignes sont matchées localement → plus
besoin d'IA pour l'identification produit, juste l'extraction brute des lignes.

C'est ce référentiel qui produit l'économie majeure long terme.
"""
from odoo import models, fields, api


class AbrmdAiProductMatch(models.Model):
    _name = "abrmd.ai.product.match"
    _description = "Matching produit fournisseur ↔ produit Odoo (apprentissage)"
    _order = "occurrences desc, last_seen_date desc"

    partner_id = fields.Many2one(
        "res.partner",
        string="Fournisseur",
        required=True,
        ondelete="cascade",
        domain="[('supplier_rank', '>', 0)]",
        index=True,
    )
    supplier_ref = fields.Char(
        string="Référence fournisseur",
        help="SKU/réf telle qu'écrite sur la facture (peut différer du default_code Odoo).",
        index=True,
    )
    supplier_name = fields.Char(
        string="Désignation fournisseur",
        help="Libellé tel qu'écrit sur la facture.",
    )
    product_id = fields.Many2one(
        "product.product",
        string="Produit Odoo",
        required=True,
        ondelete="cascade",
        index=True,
    )
    confidence = fields.Float(
        string="Confiance",
        digits=(3, 2),
        default=0.5,
    )
    occurrences = fields.Integer(string="Occurrences", default=1)
    unit_price_avg = fields.Float(
        string="Prix unitaire moyen",
        digits=(12, 4),
        help="Moyenne mobile des N derniers prix vus pour ce produit chez ce fournisseur.",
    )
    last_unit_price = fields.Float(string="Dernier prix vu", digits=(12, 4))
    last_seen_date = fields.Datetime(string="Dernière facture vue", default=fields.Datetime.now)
    is_active = fields.Boolean(string="Actif", default=True)

    _sql_constraints = [
        (
            "partner_ref_unique",
            "UNIQUE(partner_id, supplier_ref)",
            "Cette référence est déjà mappée pour ce fournisseur.",
        ),
    ]

    @api.model
    def match_line(self, partner_id, supplier_ref=None, supplier_name=None, threshold=0.8):
        """
        Cherche le best match pour cette ligne de facture.

        Stratégie :
        1. Match exact sur supplier_ref si fourni → confidence 1.0
        2. Match flou sur supplier_name (similarité simple) → si > threshold
        3. None sinon (caller doit fallback sur matching produit Odoo standard)

        Retourne (product_id, match_record, score) ou (None, None, 0.0).
        """
        if not partner_id:
            return None, None, 0.0

        # 1. Match exact supplier_ref
        if supplier_ref:
            exact = self.search([
                ("partner_id", "=", partner_id),
                ("supplier_ref", "=", supplier_ref.strip()),
                ("is_active", "=", True),
            ], limit=1)
            if exact:
                return exact.product_id, exact, 1.0

        # 2. Match flou nom
        if supplier_name:
            name_lower = supplier_name.lower().strip()
            candidates = self.search([
                ("partner_id", "=", partner_id),
                ("is_active", "=", True),
            ])
            best_score = 0.0
            best_rec = None
            for c in candidates:
                if not c.supplier_name:
                    continue
                score = self._similarity(name_lower, c.supplier_name.lower())
                if score > best_score:
                    best_score = score
                    best_rec = c
            if best_score >= threshold and best_rec:
                return best_rec.product_id, best_rec, best_score

        return None, None, 0.0

    @api.model
    def learn(self, partner_id, product_id, supplier_ref=None, supplier_name=None, unit_price=None):
        """
        Enregistre / met à jour le mapping confirmé par Anthony.

        Appelé depuis le bouton « Corriger & Apprendre » quand Anthony valide
        un product_id pour une ligne extraite par OpenAI.
        """
        domain = [
            ("partner_id", "=", partner_id),
            ("product_id", "=", product_id),
        ]
        if supplier_ref:
            domain.append(("supplier_ref", "=", supplier_ref.strip()))

        existing = self.search(domain, limit=1)
        if existing:
            new_occ = existing.occurrences + 1
            new_avg = existing.unit_price_avg
            if unit_price is not None:
                # moyenne mobile simple
                new_avg = (existing.unit_price_avg * existing.occurrences + unit_price) / new_occ
            existing.write({
                "occurrences": new_occ,
                "confidence": min(1.0, existing.confidence + 0.05),
                "supplier_name": supplier_name or existing.supplier_name,
                "unit_price_avg": new_avg,
                "last_unit_price": unit_price if unit_price is not None else existing.last_unit_price,
                "last_seen_date": fields.Datetime.now(),
            })
            return existing
        return self.create({
            "partner_id": partner_id,
            "product_id": product_id,
            "supplier_ref": (supplier_ref or "").strip() or False,
            "supplier_name": supplier_name,
            "unit_price_avg": unit_price or 0.0,
            "last_unit_price": unit_price or 0.0,
            "confidence": 0.6,
            "occurrences": 1,
        })

    @staticmethod
    def _similarity(a, b):
        """
        Similarité simple : Jaccard sur tokens (mots).
        Pas de dépendance externe (rapidfuzz/python-Levenshtein pas garantis SaaS).
        """
        if not a or not b:
            return 0.0
        sa = set(a.split())
        sb = set(b.split())
        if not sa or not sb:
            return 0.0
        inter = sa & sb
        union = sa | sb
        return len(inter) / len(union)

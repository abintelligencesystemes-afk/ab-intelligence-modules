# -*- coding: utf-8 -*-
"""
Référentiel des signatures fournisseurs.

Chaque entrée associe :
- un res.partner connu (le bon fournisseur)
- une signature textuelle (mots-clés caractéristiques : VAT, SIRET, headers,
  formules récurrentes du PDF, format de référence)
- un niveau de confiance et un nombre d'occurrences

Au scan d'une nouvelle facture, on compare le texte OCR brut (avant appel
Vision complet) avec ces signatures. Si match > 80 %, on identifie le partner
sans avoir besoin de l'inférer via OpenAI — gain de tokens.
"""
from odoo import models, fields, api


class AbrmdAiSupplierSignature(models.Model):
    _name = "abrmd.ai.supplier.signature"
    _description = "Signature OCR d'un fournisseur (apprentissage)"
    _order = "occurrences desc, last_seen_date desc"

    partner_id = fields.Many2one(
        "res.partner",
        string="Fournisseur",
        required=True,
        ondelete="cascade",
        domain="[('supplier_rank', '>', 0)]",
        index=True,
    )
    supplier_text_extracted = fields.Text(
        string="Texte OCR brut détecté",
        help="Header/footer/identifiant texte tel qu'apparu sur la facture.",
    )
    signature_keywords = fields.Text(
        string="Mots-clés signature",
        required=True,
        help="Liste de mots-clés caractéristiques séparés par virgule "
             "(VAT, SIRET, nom commercial, format ref facture, etc.).",
    )
    vat_pattern = fields.Char(
        string="Pattern VAT",
        help="VAT FR/EU exact de ce fournisseur (cache pour match rapide).",
    )
    siret_pattern = fields.Char(string="Pattern SIRET")
    confidence = fields.Float(
        string="Confiance",
        digits=(3, 2),
        default=0.5,
        help="Confiance dans cette signature (0..1). Augmente avec occurrences.",
    )
    occurrences = fields.Integer(
        string="Occurrences",
        default=1,
        help="Nombre de fois où ce match a été confirmé par Anthony.",
    )
    last_seen_date = fields.Datetime(
        string="Dernière utilisation",
        default=fields.Datetime.now,
    )
    is_active = fields.Boolean(string="Actif", default=True)
    notes = fields.Text(string="Notes")

    _sql_constraints = [
        (
            "partner_signature_unique",
            "UNIQUE(partner_id, signature_keywords)",
            "Cette signature existe déjà pour ce fournisseur.",
        ),
    ]

    @api.model
    def match(self, raw_text, threshold=0.8):
        """
        Cherche la meilleure signature qui matche le texte brut.

        Retourne (partner_id, signature_record, score) ou (None, None, 0.0).
        Utilise une similarité simple par % de mots-clés présents.
        """
        if not raw_text:
            return None, None, 0.0
        raw_lower = raw_text.lower()
        best_score = 0.0
        best_record = None
        for sig in self.search([("is_active", "=", True)]):
            keywords = [
                k.strip().lower()
                for k in (sig.signature_keywords or "").split(",")
                if k.strip()
            ]
            if not keywords:
                continue
            matched = sum(1 for k in keywords if k in raw_lower)
            score = matched / len(keywords)
            # Bonus si VAT/SIRET exact présent
            if sig.vat_pattern and sig.vat_pattern.lower() in raw_lower:
                score = min(1.0, score + 0.3)
            if sig.siret_pattern and sig.siret_pattern in raw_lower:
                score = min(1.0, score + 0.2)
            if score > best_score:
                best_score = score
                best_record = sig
        if best_score >= threshold and best_record:
            return best_record.partner_id, best_record, best_score
        return None, None, best_score

    @api.model
    def learn_or_update(self, partner_id, raw_text, vat=None, siret=None, keywords_override=None):
        """
        Crée ou met à jour la signature pour ce partner à partir du raw_text.

        Si une signature existe déjà pour ce partner_id : incrémente occurrences
        et confidence (jusqu'à 1.0). Sinon, crée une nouvelle signature en
        extrayant des keywords du raw_text.
        """
        existing = self.search([("partner_id", "=", partner_id)], limit=1)
        if existing:
            existing.write({
                "occurrences": existing.occurrences + 1,
                "confidence": min(1.0, existing.confidence + 0.05),
                "last_seen_date": fields.Datetime.now(),
            })
            return existing

        # Création : extraction keywords si pas fournis
        if not keywords_override and raw_text:
            keywords_override = self._auto_extract_keywords(raw_text, vat, siret)
        return self.create({
            "partner_id": partner_id,
            "supplier_text_extracted": (raw_text or "")[:2000],
            "signature_keywords": keywords_override or "",
            "vat_pattern": vat,
            "siret_pattern": siret,
            "confidence": 0.5,
            "occurrences": 1,
        })

    @staticmethod
    def _auto_extract_keywords(raw_text, vat=None, siret=None):
        """Extraction heuristique simple des mots significatifs (nom partner, VAT, SIRET)."""
        keywords = []
        if vat:
            keywords.append(vat)
        if siret:
            keywords.append(siret)
        # Top 5 mots > 4 chars qui ressemblent à du nom propre (capitalized)
        seen = set()
        for word in raw_text.split():
            w = word.strip(".,;:()[]")
            if len(w) >= 4 and w[0].isupper() and w.lower() not in seen:
                seen.add(w.lower())
                keywords.append(w)
                if len(keywords) >= 8:
                    break
        return ",".join(keywords)

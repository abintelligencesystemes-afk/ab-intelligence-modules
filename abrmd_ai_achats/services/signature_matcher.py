# -*- coding: utf-8 -*-
"""
Wrappers signature fournisseur pour usage depuis le pipeline learning.
"""


def find_supplier_by_text(env, raw_text, threshold=0.8):
    """
    Cherche un fournisseur via le référentiel signatures.
    Retourne (partner, signature, score) ou (None, None, 0.0).
    """
    return env["abrmd.ai.supplier.signature"].match(raw_text, threshold=threshold)


def learn_supplier(env, partner_id, raw_text, vat=None, siret=None):
    """Apprentissage signature (appelé depuis bouton Corriger & Apprendre)."""
    return env["abrmd.ai.supplier.signature"].learn_or_update(
        partner_id=partner_id,
        raw_text=raw_text,
        vat=vat,
        siret=siret,
    )

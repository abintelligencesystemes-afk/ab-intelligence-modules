# -*- coding: utf-8 -*-
"""
Wrappers matching produit pour usage depuis le pipeline.
"""


def find_product(env, partner_id, supplier_ref=None, supplier_name=None, threshold=0.8):
    """Cherche un product.product via le référentiel matching."""
    return env["abrmd.ai.product.match"].match_line(
        partner_id=partner_id,
        supplier_ref=supplier_ref,
        supplier_name=supplier_name,
        threshold=threshold,
    )


def learn_product(env, partner_id, product_id, supplier_ref=None, supplier_name=None, unit_price=None):
    """Apprentissage matching produit."""
    return env["abrmd.ai.product.match"].learn(
        partner_id=partner_id,
        product_id=product_id,
        supplier_ref=supplier_ref,
        supplier_name=supplier_name,
        unit_price=unit_price,
    )

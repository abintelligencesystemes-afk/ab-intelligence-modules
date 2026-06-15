# -*- coding: utf-8 -*-
"""Endpoint /abis_colors/<id>.css — sert le CSS dynamique par compagnie."""
from odoo import http
from odoo.http import request


class AbisCompanyColorsController(http.Controller):
    @http.route(
        "/abis_colors/<int:company_id>.css",
        type="http",
        auth="public",
        methods=["GET"],
    )
    def serve_company_css(self, company_id):
        company = (
            request.env["res.company"]
            .sudo()
            .browse(company_id)
            .exists()
        )
        if not company:
            return request.not_found()
        css = company.get_abis_css()
        headers = [
            ("Content-Type", "text/css; charset=utf-8"),
            ("Cache-Control", "public, max-age=3600"),
        ]
        return request.make_response(css, headers=headers)

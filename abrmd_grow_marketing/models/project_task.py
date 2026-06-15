# -*- coding: utf-8 -*-
"""Extension project.task : bouton 'Générer post Grow' + relation inverse posts."""
from odoo import _, fields, models


class ProjectTask(models.Model):
    _inherit = "project.task"

    abrmd_grow_post_ids = fields.One2many(
        comodel_name="abrmd.grow.post",
        inverse_name="task_id",
        string="Posts Grow Marketing",
    )
    abrmd_grow_post_count = fields.Integer(
        string="Nb posts Grow",
        compute="_compute_abrmd_grow_post_count",
    )

    def _compute_abrmd_grow_post_count(self):
        for rec in self:
            rec.abrmd_grow_post_count = len(rec.abrmd_grow_post_ids)

    def action_open_abrmd_grow_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Générer post via Anthony Growth Agent"),
            "res_model": "abrmd.grow.generate.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_source_model": "project.task",
                "default_source_res_id": self.id,
                "default_task_id": self.id,
                "default_project_id": self.project_id.id,
            },
        }

    def action_view_abrmd_grow_posts(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Posts Grow"),
            "res_model": "abrmd.grow.post",
            "view_mode": "list,form,kanban,calendar",
            "domain": [("task_id", "=", self.id)],
            "context": {"default_task_id": self.id},
        }

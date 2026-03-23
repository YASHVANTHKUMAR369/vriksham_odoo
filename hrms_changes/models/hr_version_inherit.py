from odoo import models, fields, api, _


class HrVersion(models.Model):
    _inherit = 'hr.version'

    tds_amount = fields.Float(string="TDS Amount")
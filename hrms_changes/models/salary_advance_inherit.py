from odoo import fields, models


class SalaryAdvance(models.Model):
    _inherit = 'salary.advance'

    paid = fields.Boolean(string='Paid', default=False)
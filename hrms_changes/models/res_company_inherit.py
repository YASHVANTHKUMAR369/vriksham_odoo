from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    hr_signature = fields.Image(string='HR Signature')
    hr_name = fields.Char(string='HR Name')

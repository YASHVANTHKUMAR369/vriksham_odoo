from odoo import models, fields

class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    
    late_count = fields.Integer(default=0)
    missing_punch_count = fields.Integer(default=0)

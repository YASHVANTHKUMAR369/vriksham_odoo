from odoo import models, fields, api, _


class HrEmployeeDocument(models.Model):
    _inherit = 'hr.employee.document'
    _description = 'HR Employee Documents'

    received = fields.Boolean(string="Verified")
from odoo import models, fields, api

class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    identification_id = fields.Char(related="employee_id.identification_id", string="Emp. Code")
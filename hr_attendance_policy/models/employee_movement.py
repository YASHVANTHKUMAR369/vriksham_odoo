from odoo import models, fields

class EmployeeMovement(models.Model):
    _name = 'employee.movement'
    _description = 'Employee Movement Register'

    employee_id = fields.Many2one('hr.employee', required=False)
    purpose = fields.Char(required=False)
    exit_time = fields.Datetime(required=False)
    return_time = fields.Datetime()

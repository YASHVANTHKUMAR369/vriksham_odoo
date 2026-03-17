from odoo import models, fields

class HrEmployee(models.Model):
    _inherit = "hr.employee"

    expense_approval_step_ids = fields.One2many(
        'hr.expense.approval.step',
        'employee_id',
        string="Expense Approval Steps"
    )

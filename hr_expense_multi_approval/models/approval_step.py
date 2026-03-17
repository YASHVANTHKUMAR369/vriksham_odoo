from odoo import models, fields

class HrExpenseApprovalStep(models.Model):
    _name = "hr.expense.approval.step"
    _description = "Expense Approval Step"
    _order = "sequence"

    name = fields.Char(required=True)
    sequence = fields.Integer(required=True)

    # 🔥 NEW FIELD
    employee_id = fields.Many2one(
        'hr.employee',
        string="Employee",
        ondelete='cascade',
        required=True,
    )

    approve_by = fields.Selection([
        ('manager', 'Employee Manager'),
        ('department_manager', 'Department Manager'),
        # ('expense_manager', 'Expense Manager'),
        ('specific_user', 'Specific User'),
    ], required=True, default='specific_user')

    user_id = fields.Many2one(
        'res.users',
        string="User",
        domain=lambda self: [
            ('active', '=', True),
            ('group_ids', 'in', [self.env.ref('hr_expense.group_hr_expense_user').id,self.env.ref('hr_expense.group_hr_expense_manager').id]),
        ]
    )

    min_amount = fields.Float()
    max_amount = fields.Float(default=99999999)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

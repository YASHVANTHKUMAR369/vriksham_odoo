from odoo import models, fields

class HrEmployeeLeaveConfig(models.Model):
    _name = 'hr.employee.leave.config'
    _description = 'Employee Leave Configuration'
    _rec_name = 'employee_id'

    _sql_constraints = [
        (
            'unique_employee_config',
            'unique(employee_id)',
            'Leave configuration already exists for this employee.'
        )
    ]

    employee_id = fields.Many2one(
        'hr.employee',
        string="Employee",
        required=True,
        ondelete='cascade'
    )

    # ---------------- Casual Leave (CL) ----------------
    cl_balance = fields.Float(string="Available CL", default=0.0)
    cl_yearly_days = fields.Float(string="CL / Year", default=6)
    cl_monthly_credit = fields.Float(string="CL / Month", default=0.5)
    cl_after_probation = fields.Boolean(
        string="Eligible After Probation",
        default=True
    )
    cl_lapse_year_end = fields.Boolean(
        string="Lapse at Year End",
        default=True
    )
    cl_allowed_notice = fields.Boolean(
        string="Allowed During Notice Period",
        default=False
    )

    # ---------------- Earned Leave (EL) ----------------
    el_balance = fields.Float(string="Available EL", default=0.0)
    el_yearly_days = fields.Float(string="EL / Year", default=12)
    el_usable_after_months = fields.Integer(
        string="EL Usable After (Months)",
        default=12
    )
    el_credit_year_end = fields.Boolean(
        string="Credit on 31st December",
        default=True
    )
    el_max_accumulation = fields.Float(
        string="Max EL Accumulation",
        default=30
    )

    active = fields.Boolean(default=True)

from odoo import models, fields
from datetime import date

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    probation_end_date = fields.Date(string="Probation End Date")
    notice_start_date = fields.Date(string="Notice Start Date")

    leave_config_id = fields.One2many(
        'hr.employee.leave.config',
        'employee_id',
        string="Leave Configuration"
    )

    def is_on_probation(self):
        self.ensure_one()
        return bool(
            self.probation_end_date and date.today() < self.probation_end_date
        )

    def is_on_notice(self):
        self.ensure_one()
        return bool(self.notice_start_date)

class HrLeave(models.Model):
    _inherit = "hr.leave"

    def action_approve(self, check_state=True):
        res = super().action_approve(check_state)
        self._check_overtime_deductible(self)
        self._casual_earned_leave()
        return res

    def _casual_earned_leave(self):
        for rec in self:
            employee_id = self.env['hr.employee.leave.config'].search([('employee_id', '=', rec.employee_id.id)])
            for emp in employee_id:
                if emp and emp.el_balance:
                    print("LEAVE")
                    leave = emp.el_balance - rec.number_of_days
                    print(leave,"QWERTYT")
                    emp.write({
                        'el_balance': leave
                    })
                else:
                    emp.write({
                        'el_balance': 0.0
                    })
# -*- coding: utf-8 -*-
from datetime import date
from odoo import fields, models, _
from odoo.exceptions import ValidationError


class EmployeeAttendanceReport(models.TransientModel):
    _name = 'employee.attendance.report'
    _description = 'Employee Attendance Report Wizard'

    from_date = fields.Date('From Date', help="Starting date for report")
    to_date = fields.Date('To Date', help="Ending date for report")
    employee_ids = fields.Many2many('hr.employee', string='Employee',
                                    help='Name of Employee')
    # identification_ids = fields.Many2many('canteen.attendance', string='Employee Id', help='Emp. Identification No.')
    emp_code = fields.Char(string='Employee Id', help='Emp. Identification No.')
    company_id = fields.Many2one('res.company', string="Company", required=True)

    def action_print_xlsx(self):
        """Return direct XLSX URL (same as Stock Picking XLSX)"""

        if not self.from_date:
            self.from_date = date.today()
        if not self.to_date:
            self.to_date = date.today()

        if self.from_date > self.to_date:
            raise ValidationError(_('From Date must be earlier than To Date.'))
        
        # If employee selected but no attendance, raise error
        if self.employee_ids:
           
            attendances = self.env['hr.attendance'].search([
                ('employee_id', 'in', self.employee_ids.ids),
            ])
            if not attendances:
                raise ValidationError(_("No attendance records found."))
        elif self.emp_code:
            attendances = self.env['hr.attendance'].search([
                ('identification_id', 'in', [self.emp_code])
            ])
            if not attendances:
                raise ValidationError(_("No attendance records found"))
        if self.company_id not in self.env.user.company_ids:
            raise ValidationError(_("You are not allowed to print other company report"))

        # Return controller route instead of ir.actions.report
        return {
            'type': 'ir.actions.act_url',
            'url': f'/employee_attendance/xlsx/{self.id}',
            'target': 'self',
        }

# -*- coding: utf-8 -*-

# from odoo import models, fields, api
import logging
from odoo import models, fields, api
from datetime import datetime
from datetime import timedelta

_logger = logging.getLogger(__name__)


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def compute_attendance_workdays(self):
        print("=== Running compute_attendance_workdays ===")
        for payslip in self:
            start_date, end_date = payslip.date_from, payslip.date_to
            employee_id = payslip.employee_id.id

            # Count unique attendance days
            attendances = self.env['hr.attendance'].search([
                ('employee_id', '=', employee_id),
                ('check_in', '>=', start_date),
                ('check_in', '<=', end_date)
            ])
            print(f"Total Attendance Records: {len(attendances)}")
            workdays = len(set(att.check_in.date() for att in attendances))
            contract = payslip.contract_id


            work_schedule = contract.resource_calendar_id  # Employee's Work Schedule
            total_workdays = 0
            current_date = start_date

            while current_date <= end_date:
               # Get weekday (0=Monday, 6=Sunday)
               weekday = current_date.weekday()

               # Check if this weekday exists in the work schedule
               if work_schedule.attendance_ids.filtered(lambda a: int(a.dayofweek) == weekday):
                   total_workdays += 1

               current_date += timedelta(days=1)

            work_entry = payslip.worked_days_line_ids.filtered(lambda w: w.code == 'WORK100')
            if work_entry:
                work_entry.update({'number_of_days': total_workdays})

            # Count leaves (Casual, Paid, etc.)
            leaves = self.env['hr.leave'].search([
                ('employee_id', '=', employee_id),
                ('request_date_from', '>=', start_date),
                ('request_date_to', '<=', end_date),
                ('state', '=', 'validate')
            ])
            
            leave_types = self.env['hr.leave.type'].search([])
            leave_days = {leave_type.name: 0 for leave_type in leave_types}

            for leave in leaves:
                leave_days[leave.holiday_status_id.name] += 1

            # Add to payslip worked days
            worked_days_lines = [
                ('ATTENDANCE', 'Worked Days', workdays)
            ] + [
                (leave_type.name.upper().replace(' ', '_'), leave_type.name, leave_days[leave_type.name])
                for leave_type in leave_types
            ]

            # #----------Calculate Loss Of Pay--------
            # el_days = 0.0
            # cl_days = 0.0

            # for leave in leaves:
            #     leave_days = leave.number_of_days
            #     if leave.holiday_status_id.name == 'Earned Leave':
            #         el_days += leave_days
            #     elif leave.holiday_status_id.name == 'Casual Leave':
            #         cl_days += leave_days
            # el_balance = 0.0
            # cl_balance = 0.0
           
            # # Calculate excess leaves → Loss of Pay
            # lop_days = 0.0
            # # Apply cap: Allow 1 EL and 2 CL per month
            # allowed_el = 1.0
            # allowed_cl = 2.0

            # # Calculate excess leaves
            # excess_el = max(0.0, el_days - allowed_el)
            # excess_cl = max(0.0, cl_days - allowed_cl)

            # sick_days = 0.0
            # unpaid_days = 0.0

            # for leave in leaves:
            #     days = (min(leave.request_date_to, end_date) - max(leave.request_date_from, start_date)).days + 1
            #     if leave.request_unit_half:
            #         days = 0.5
            #     if leave.holiday_status_id.name == 'Sick Time Off':
            #         sick_days += days
            #     elif leave.holiday_status_id.name == 'Unpaid Leave':
            #         unpaid_days = days

            # lop_days = sick_days + unpaid_days

            # worked_days_lines.append(('LOP', 'Loss Of Pay', lop_days))

            # Count public holidays
            public_holidays = self.env['resource.calendar.leaves'].search([
                # ('calendar_id', '=', work_schedule.id),
                ('date_from', '>=', start_date),
                ('date_to', '<=', end_date),
                ('resource_id', '=', False)  # Public holidays have no specific resource
            ])

            public_holiday_days = sum((holiday.date_to - holiday.date_from).days + 1 for holiday in public_holidays)
            worked_days_lines.append(('PUBLIC_HOLIDAY', 'Public Holidays', public_holiday_days))
            #append casual leave
           
            # worked_days = cl_days + lop_days
            # total_work_days = total_workdays - worked_days

            # worked_days_lines.append(('ATTENDANCE', 'Worked Days', workdays))
            # worked_days_lines.append(('ATTENDANCE', 'Worked Days', total_work_days))
            for code, name, days in worked_days_lines:
                line = payslip.worked_days_line_ids.filtered(lambda wd: wd.code == code)
                if line:
                    line.number_of_days = days
                else:
                    payslip.worked_days_line_ids.create({
                        'payslip_id': payslip.id,
                        'name': name,
                        'code': code,
                        'number_of_days': days,
                        'contract_id': payslip.contract_id.id,
                    })

    def action_compute_sheet(self):
        print("Calculation staring.........")
        _logger.info("=== Running Payroll Calculation ===")
        self.compute_attendance_workdays()
        res = super(HrPayslip, self).action_compute_sheet()
        return res

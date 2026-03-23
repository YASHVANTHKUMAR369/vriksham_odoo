from odoo import models, fields, api, _, tools
from datetime import date, datetime, time, timedelta
import babel
from dateutil.relativedelta import relativedelta
from collections import defaultdict


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    days_calculation = fields.Html(string='Days Calculation')
    # loan_ids = fields.Many2many(
    #     comodel_name="hr.loan.line",
    #     string="Loan Records",
    #     domain="[('employee_id', '=', employee_id), ('paid', '=', False)]"
    # )
    variable_pay = fields.Float(string="Variable Pay")
    net_salary = fields.Float(string="Net Salary", compute='compute_net_salary')
    gross_salary = fields.Float(string="Gross Salary", compute='compute_net_salary')

    @api.depends('line_ids')
    def compute_net_salary(self):
        for payslip in self:
            payslip.net_salary = 0
            payslip.gross_salary = 0
            for line in payslip.line_ids:
                if line.category_id.id == self.env.ref('hr_payroll_community.NET').id:
                    payslip.net_salary = line.total
                if line.category_id.id == self.env.ref('hr_payroll_community.GROSS').id:
                    payslip.gross_salary = line.total

    struct_id = fields.Many2one(comodel_name='hr.payroll.structure',
                                string='Structure',
                                help='Defines the rules that have to be applied'
                                     ' to this payslip, accordingly '
                                     'to the contract chosen. If you let empty '
                                     'the field contract, this field isn\'t '
                                     'mandatory anymore and thus the rules '
                                     'applied will be all the rules set on the '
                                     'structure of all contracts of the '
                                     'employee valid for the chosen period', related="contract_id.struct_id")
    def compute_days_summary(self):
        leave_details = self.get_worked_day_lines(self.contract_id, self.date_from, self.date_to)
        # loan_ids = self.env['hr.loan.line'].search(
        #     [('employee_id', '=', self.employee_id.id), ('date', '>=', self.date_from),
        #      ('date', '<=', self.date_to)]).ids
        # self.loan_ids = loan_ids if loan_ids else False
        """
        Compute summary data: total days, attendance, applied/unapplied leaves, wages, leave breakdown.
        Returns a dictionary with all relevant info.
        """
        total_days = (self.date_to - self.date_from).days + 1
        wage = self.contract_id.wage
        per_day_salary = wage / total_days if total_days else 0.0

        # Attendances
        attendance_data = self.env['hr.attendance'].read_group(
            [
                ('employee_id', '=', self.employee_id.id),
                ('check_in', '>=', self.date_from),
                ('check_in', '<=', self.date_to),
            ],
            ['employee_id'],  # fields (NO :day here)
            ['employee_id', 'check_in:month', 'check_in:day'],  # groupby only
            lazy=False
        )
        attendance_days = len(attendance_data) if attendance_data else 0
        public_holidays_days = self.env['resource.calendar.leaves'].search_count([
            ('calendar_id', '=', self.employee_id.resource_calendar_id.id),
            ('resource_id', '=', False),
            ('date_from', '>=', self.date_from),
            ('date_to', '<=', self.date_to),
        ])
        # Valid leaves
        leave_ids = self.env['hr.leave'].search([
            ('employee_id', '=', self.employee_id.id),
            ('state', '=', 'validate'),
        ])
        week_days = list(set(self.employee_id.resource_calendar_id.attendance_ids.mapped('dayofweek')))
        week_off_count = 0
        current_day = self.date_from
        while current_day <= self.date_to:
            if str(current_day.weekday()) not in week_days:
                week_off_count+=1
            current_day += timedelta(days=1)
        paid_leaves = {}
        unpaid_leaves = {}
        applied_leaves = 0

        for leave in leave_ids:
            leave_cat = leave.holiday_status_id
            if leave_cat.code not in ['EEL', 'CD', 'PER']:
                if leave_cat.request_unit == 'day':
                    days = leave.get_actual_leave(to_date=self.date_to, from_date=self.date_from)
                else:
                    days = leave.number_of_days

                applied_leaves += days
                # Determine if it's paid or unpaid
                target = paid_leaves if leave_cat.time_type != 'leave' else unpaid_leaves

                # Add or accumulate days for the same leave type
                if leave_cat.name in target:
                    target[leave_cat.name] += days
                else:
                    target[leave_cat.name] = days

        # Convert dicts back to list of dicts for display
        paid_leaves_list = [{'name': k, 'days': v} for k, v in paid_leaves.items()]
        unpaid_leaves_list = [{'name': k, 'days': v} for k, v in unpaid_leaves.items()]

        unapplied_leave_days = round(max(total_days - attendance_days - applied_leaves - public_holidays_days - week_off_count, 0), 2)
        lop_day = unapplied_leave_days
        for i in unpaid_leaves_list:
            lop_day += i['days']
        return {
            'total_days': total_days,
            'attendance_days': attendance_days,
            'public_holidays_days': public_holidays_days,
            'week_off_count': week_off_count,
            'applied_leaves': round(applied_leaves, 2),
            'unapplied_leaves': unapplied_leave_days,
            'lop_day': lop_day,
            'wage': round(wage, 2),
            'per_day_salary': round(per_day_salary, 2),
            'paid_leaves': paid_leaves_list,
            'unpaid_leaves': unpaid_leaves_list,
        }

    def _compute_get_days_calculation_data(self):
        self.days_calculation = False
        data = self.compute_days_summary()

        html_content = f"""
        <div class="days-calc-container" style="display: flex; gap: 30px; flex-wrap: wrap;">

            <!-- LEFT SIDE SUMMARY -->
            <div class="summary-card p-3 border rounded shadow-sm" style="flex: 1; min-width: 250px; background-color: #f8f9fa;">
                <h4 class="mb-3">Summary</h4>
                <table class="table table-sm table-bordered mb-0">
                    <tbody>
                        <tr>
                            <th>Total Days</th>
                            <td class="text-end">{data['total_days']}</td>
                        </tr>
                        <tr>
                            <th>Public Holidays</th>
                            <td class="text-end">{data['public_holidays_days']}</td>
                        </tr>
                        <tr>
                            <th>Attendance Days</th>
                            <td class="text-end">{data['attendance_days']}</td>
                        </tr>
                        <tr>
                            <th>Week Off</th>
                            <td class="text-end">{data['week_off_count']}</td>
                        </tr>
                        <tr>
                            <th>Applied Leave Days</th>
                            <td class="text-end">{data['applied_leaves']}</td>
                        </tr>
                        <tr>
                            <th>Unapplied Leave</th>
                            <td class="text-end">{data['unapplied_leaves']}</td>
                        </tr>
                        <tr>
                            <th>Wage</th>
                            <td class="text-end">{data['wage']}</td>
                        </tr>
                        <tr>
                            <th>Per Day Salary</th>
                            <td class="text-end">{data['per_day_salary']}</td>
                        </tr>
                        <tr>
                            <th>Lop Days</th>
                            <td class="text-end">{data['lop_day']}</td>
                        </tr>
                    </tbody>
                </table>
            </div>

            <!-- RIGHT SIDE LEAVES -->
            <div class="leave-card p-3 border rounded shadow-sm" style="flex: 1; min-width: 300px; background-color: #ffffff;">
                <h4 class="mb-3 text-success">Paid Leaves</h4>
                <table class="table table-sm table-striped table-bordered mb-3">
                    <thead class="table-light">
                        <tr>
                            <th>Leave Name</th>
                            <th class="text-end">Days</th>
                        </tr>
                    </thead>
                    <tbody>
        """

        # Paid Leaves
        if data['paid_leaves']:
            for leave in data['paid_leaves']:
                html_content += f"""
                        <tr>
                            <td>{leave['name']}</td>
                            <td class="text-end">{leave['days']}</td>
                        </tr>
                """
        else:
            html_content += """
                        <tr>
                            <td colspan="2" class="text-center">No Paid Leaves</td>
                        </tr>
            """

        html_content += """
                    </tbody>
                </table>

                <h4 class="mb-3 text-danger">Unpaid Leaves</h4>
                <table class="table table-sm table-striped table-bordered">
                    <thead class="table-light">
                        <tr>
                            <th>Leave Name</th>
                            <th class="text-end">Days</th>
                        </tr>
                    </thead>
                    <tbody>
        """

        # Unpaid Leaves
        if data['unpaid_leaves']:
            for leave in data['unpaid_leaves']:
                html_content += f"""
                        <tr>
                            <td>{leave['name']}</td>
                            <td class="text-end">{leave['days']}</td>
                        </tr>
                """
        else:
            html_content += """
                        <tr>
                            <td colspan="2" class="text-center">No Unpaid Leaves</td>
                        </tr>
            """

        html_content += """
                    </tbody>
                </table>
            </div>
        </div>

        <style>
            .days-calc-container h4 { font-weight: 600; }
            .summary-card th, .leave-card th { width: 60%; }
            .summary-card td, .leave-card td { width: 40%; }
            .text-end { text-align: right; }
        </style>
        """

        self.days_calculation = html_content


    def _check_dates(self):
        return

    @api.onchange('employee_id')
    def onchange_employee(self):
        if (not self.employee_id) or (not self.date_from):
            return
        employee = self.employee_id
        date_from = self.date_from
        date_to = self.date_to
        self.name = _('Salary Slip of %s for %s - %s') % (
            employee.name, date_from.strftime('%d/%m/%Y'), date_to.strftime('%d/%m/%Y'))
        self.company_id = employee.company_id
        if not self.env.context.get('contract') or not self.contract_id:
            contract_ids = self.get_contract(employee, date_from, date_to)
            self.contract_id = self.env['hr.version'].browse(contract_ids[0]) if contract_ids else None
            self.struct_id = self.contract_id.struct_id or False
        self._compute_get_days_calculation_data()


    def action_compute_sheet(self):
        for rec in self:
            rec._compute_get_days_calculation_data()
        return super().action_compute_sheet()

    @api.onchange('date_from')
    def onchange_date_from(self):
        if self.date_from:
            self.date_to = self.date_from + relativedelta(months=+1, day=1, days=-1)
        worked_days_line_ids = self.get_worked_day_lines(self.contract_id, self.date_from,
                                                         self.date_to)
        worked_days_lines = self.worked_days_line_ids.browse([])
        for r in worked_days_line_ids:
            worked_days_lines += worked_days_lines.new(r)
        self._compute_get_days_calculation_data()
        return

    def onchange_date_to(self):
        return




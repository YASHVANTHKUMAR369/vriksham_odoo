import base64

from odoo import models, fields, api, _, tools
from odoo.exceptions import UserError
from datetime import date, datetime, time, timedelta
import babel
from dateutil.relativedelta import relativedelta
from collections import defaultdict

class HrLeave(models.Model):
    _inherit = 'hr.leave'


    def get_actual_leave(self, from_date, to_date):
        self.ensure_one()
        value = 0

        leave_start = self.request_date_from
        leave_end = self.request_date_to

        # No overlap
        if to_date < leave_start or from_date > leave_end:
            return value

        # Overlapping period
        overlap_start = max(from_date, leave_start)
        overlap_end = min(to_date, leave_end)

        # Get working days from employee calendar
        week_days = list(set(
            self.employee_id.resource_calendar_id.attendance_ids.mapped('dayofweek')
        ))

        week_off_count = 0
        current_day = overlap_start

        while current_day <= overlap_end:
            if str(current_day.weekday()) not in week_days:
                week_off_count += 1
            current_day += timedelta(days=1)

        # Total overlapping days
        total_days = (overlap_end - overlap_start).days + 1

        # Actual leave excluding week offs
        value = total_days - week_off_count

        return value

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    days_calculation = fields.Html(string='Days Calculation')
    loan_ids = fields.Many2many(
        comodel_name="hr.loan.line",
        string="Loan Records",
        domain="[('employee_id', '=', employee_id), ('paid', '=', False)]"
    )
    salary_advance_ids = fields.Many2many(
        comodel_name="salary.advance",
        string="Salary Advances",
        domain="[('employee_id', '=', employee_id), ('state', '=', 'approve'), ('paid', '=', False)]"
    )
    variable_pay = fields.Float(string="Variable Pay")
    net_salary = fields.Float(string="Net Salary", compute='compute_net_salary')
    gross_salary = fields.Float(string="Gross Salary", compute='compute_net_salary')
    journal_entry_id = fields.Many2one('account.move', string='Journal Entry', readonly=True, copy=False)
    journal_entry_count = fields.Integer(string='Journal Entries', compute='_compute_journal_entry_count')
    journal_entry_status = fields.Selection(
        [
            ('not_paid', 'Not Paid'),
            ('paid', 'Paid'),
            ('reversed', 'Reversed'),
        ],
        string='Journal Entry Status',
        compute='_compute_journal_entry_status',
        store=False,
    )
    payslip_calculation_html = fields.Html(string='Payslip Calculation', compute='_compute_payslip_calculation_html', store=False)

    def _compute_journal_entry_count(self):
        for rec in self:
            rec.journal_entry_count = 1 if rec.journal_entry_id else 0

    @api.depends('journal_entry_id', 'journal_entry_id.state', 'journal_entry_id.reversal_move_ids.state', 'journal_entry_id.reversed_entry_id.state')
    def _compute_journal_entry_status(self):
        for rec in self:
            status = 'not_paid'
            move = rec.journal_entry_id
            if move:
                has_posted_reversal = bool(move.reversal_move_ids.filtered(lambda m: m.state == 'posted'))
                is_reversal_move = bool(move.reversed_entry_id and move.reversed_entry_id.state == 'posted')
                if has_posted_reversal or is_reversal_move:
                    status = 'reversed'
                elif move.state == 'posted':
                    status = 'paid'
            rec.journal_entry_status = status

    def _get_monthly_payable_earning_rows(self):
        self.ensure_one()
        if not self.contract_id or not self.contract_id.salary_calculation_id:
            return []

        data = self.contract_id.salary_payslip
        rows = []
        for category in ('basic', 'main_allowance', 'other_allowance'):
            for rec in data.get(category, {}).values():
                rows.append((rec['name'], rec['amount'] / 12))
        return rows

    def _prepare_salary_calculation_data(self):
        self.ensure_one()
        if not self.contract_id or not self.contract_id.salary_calculation_id:
            return False

        data = self.contract_id.salary_payslip
        summary = self.compute_days_summary()
        earning_rows = self._get_monthly_payable_earning_rows()

        gross_salary = sum(amount for _, amount in earning_rows)
        per_day_salary = summary.get('per_day_salary', 0)
        lop_days = summary.get('lop_day', 0)
        lop_amount = per_day_salary * lop_days

        contract = self.contract_id
        employee_pf = contract.employee_pf or 0
        professional_tax = contract.professional_tax or 0
        tds_amount = contract.tds_amount or 0
        loan_amount = self._get_loan_deduction_total()
        salary_advance_amount = self._get_salary_advance_deduction_total()
        input_lines = [(line.name, line.amount) for line in self.input_line_ids if line.amount]

        payroll_adjustment_rows = [
            ('LOP Amount', -lop_amount),
            ('Loan Amount', -loan_amount),
            ('Salary Advance', -salary_advance_amount),
            ('Employee PF', -employee_pf),
            ('Professional Tax', -professional_tax),
            ('TDS', -tds_amount),
        ]

        # Keep only non-zero rows; input lines can be positive or negative adjustments.
        right_rows = [row for row in payroll_adjustment_rows if row[1]]
        right_rows.extend(input_lines)

        net_salary = gross_salary + sum(amount for _, amount in right_rows)

        return {
            'summary': summary,
            'earning_rows': earning_rows,
            'gross_salary': gross_salary,
            'right_rows': right_rows,
            'net_salary': net_salary,
            'per_day_salary': per_day_salary,
            'lop_days': lop_days,
        }

    @api.depends('contract_id', 'date_from', 'date_to', 'input_line_ids')
    def compute_net_salary(self):
        for payslip in self:
            payslip.gross_salary = 0
            payslip.net_salary = 0
            try:
                calc_data = payslip._prepare_salary_calculation_data()
                if not calc_data:
                    continue

                payslip.gross_salary = calc_data['gross_salary']
                payslip.net_salary = calc_data['net_salary']
            except Exception:
                pass

    def _get_loan_deduction_total(self):
        self.ensure_one()
        if not self.loan_ids:
            return 0.0

        return sum(self.loan_ids.mapped('amount'))

    def _get_salary_advance_deduction_total(self):
        self.ensure_one()
        if not self.salary_advance_ids:
            return 0.0

        return sum(self.salary_advance_ids.mapped('advance'))

    @property
    def emp_company(self):
        return self.company_id.display_name if self.company_id else None

    @property
    def emp_hr_name(self):
        return self.company_id.hr_name if self.company_id and self.company_id.hr_name else "-"

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

        # LOP base should be monthly payable earnings only, matching salary tab calculations.
        wage = round(sum(amount for _, amount in self._get_monthly_payable_earning_rows()), 2)
        per_day_salary = round(wage / total_days, 2) if total_days else 0.0

        calendar = self.employee_id.resource_calendar_id or self.contract_id.resource_calendar_id

        # Attendances — compute day credit based on shift (calendar) hours.
        attendance_records = self.env['hr.attendance'].search([
            ('employee_id', '=', self.employee_id.id),
            ('check_in', '>=', datetime.combine(self.date_from, time.min)),
            ('check_in', '<=', datetime.combine(self.date_to, time.max)),
        ])
        attendance_days = 0.0
        if attendance_records:
            attendance_hours_by_day = defaultdict(float)
            for attendance in attendance_records:
                if not attendance.check_in:
                    continue
                work_date = attendance.check_in.astimezone().date()
                attendance_hours_by_day[work_date] += max(attendance.worked_hours or 0.0, 0.0)

            shift_hours_by_weekday = defaultdict(float)
            if calendar and calendar.attendance_ids:
                for shift in calendar.attendance_ids:
                    shift_hours_by_weekday[shift.dayofweek] += max((shift.hour_to or 0.0) - (shift.hour_from or 0.0), 0.0)

            if shift_hours_by_weekday:
                for work_date, worked_hours in attendance_hours_by_day.items():
                    expected_hours = shift_hours_by_weekday.get(str(work_date.weekday()), 0.0)
                    if expected_hours > 0:
                        attendance_days += min(worked_hours / expected_hours, 1.0)
            else:
                week_days = set(calendar.attendance_ids.mapped('dayofweek')) if calendar else {'0', '1', '2', '3', '4', '5', '6'}
                attendance_days = float(sum(1 for work_date in attendance_hours_by_day if str(work_date.weekday()) in week_days))

        attendance_days = round(attendance_days, 2)

        public_holidays_days = 0
        if self.employee_id:
            tz_employee = self.employee_id.with_context(
                tz=(self.employee_id.tz or (calendar.tz if calendar else False) or self.env.user.tz)
            )
            public_holiday_leaves = self.employee_id._get_public_holidays(
                datetime.combine(self.date_from, time.min),
                datetime.combine(self.date_to, time.max),
            )

            public_holiday_dates = set()
            for holiday in public_holiday_leaves:
                start_dt = fields.Datetime.to_datetime(holiday.date_from)
                end_dt = fields.Datetime.to_datetime(holiday.date_to)
                local_start_date = fields.Datetime.context_timestamp(tz_employee, start_dt).date()
                local_end_date = fields.Datetime.context_timestamp(tz_employee, end_dt).date()

                start_date = max(local_start_date, self.date_from)
                end_date = min(local_end_date, self.date_to)
                current_date = start_date
                while current_date <= end_date:
                    public_holiday_dates.add(current_date)
                    current_date += timedelta(days=1)

            override_leave_dates = set()
            override_leaves = self.env['hr.leave'].search([
                ('employee_id', '=', self.employee_id.id),
                ('state', '=', 'validate'),
                ('holiday_status_id.include_public_holidays_in_duration', '=', True),
                ('request_date_from', '<=', self.date_to),
                ('request_date_to', '>=', self.date_from),
            ])
            for leave in override_leaves:
                start_date = max(leave.request_date_from, self.date_from)
                end_date = min(leave.request_date_to, self.date_to)
                current_date = start_date
                while current_date <= end_date:
                    if current_date in public_holiday_dates:
                        override_leave_dates.add(current_date)
                    current_date += timedelta(days=1)

            public_holidays_days = len(public_holiday_dates - override_leave_dates)
        # Valid leaves
        leave_ids = self.env['hr.leave'].search([
            ('employee_id', '=', self.employee_id.id),
            ('state', '=', 'validate'),
        ])
        week_days = list(set(calendar.attendance_ids.mapped('dayofweek'))) if calendar else ['0', '1', '2', '3', '4', '5', '6']
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
            if leave_cat.request_unit == 'day':
                days = leave.get_actual_leave(to_date=self.date_to, from_date=self.date_from)
            else:
                days = leave.number_of_days

            if days <= 0:
                continue

            applied_leaves += days
            # Use leave type policy for paid/unpaid split.
            target = unpaid_leaves if leave_cat.unpaid else paid_leaves

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

    def _compute_payslip_calculation_html(self):
        for payslip in self:
            try:
                calc_data = payslip._prepare_salary_calculation_data()
                if not calc_data:
                    payslip.payslip_calculation_html = False
                    continue

                summary = calc_data['summary']
                per_day_salary = calc_data['per_day_salary']
                lop_days = calc_data['lop_days']
                total_monthly = calc_data['gross_salary']
                net_salary = calc_data['net_salary']
                left_rows = calc_data['earning_rows'] + [('Gross Salary', total_monthly)]
                right_rows = calc_data['right_rows'] + [('Net Salary', net_salary)]
                total_rows = max(len(left_rows), len(right_rows))

                def _fmt_amount(amount):
                    return f"{amount:,.2f}" if amount >= 0 else f"- {abs(amount):,.2f}"

                html = f"""
                <table style="width:100%; border-collapse:collapse; font-size:14px; margin-bottom:8px; color:#111827 !important; background-color:#ffffff !important;">
                    <tbody>
                        <tr style="background-color:#dce8f5 !important; color:#111827 !important;">
                            <td style="width:16.66%; border:1px solid #374151; padding:6px; font-weight:bold; color:#111827 !important; background-color:#dce8f5 !important;">Wage (Monthly)</td>
                            <td style="width:16.66%; border:1px solid #374151; padding:6px; text-align:right; font-weight:bold; color:#111827 !important; background-color:#dce8f5 !important;">{summary.get('wage', 0):,.2f}</td>
                            <td style="width:16.66%; border:1px solid #374151; padding:6px; font-weight:bold; color:#111827 !important; background-color:#dce8f5 !important;">Per Day Salary</td>
                            <td style="width:16.66%; border:1px solid #374151; padding:6px; text-align:right; font-weight:bold; color:#111827 !important; background-color:#dce8f5 !important;">{per_day_salary:,.2f}</td>
                            <td style="width:16.66%; border:1px solid #374151; padding:6px; font-weight:bold; color:#111827 !important; background-color:#dce8f5 !important;">LOP Days</td>
                            <td style="width:16.66%; border:1px solid #374151; padding:6px; text-align:right; font-weight:bold; color:#111827 !important; background-color:#dce8f5 !important;">{lop_days}</td>
                        </tr>
                    </tbody>
                </table>
                <table style="width:100%; border-collapse:collapse; font-size:14px; table-layout:fixed; color:#111827 !important; background-color:#ffffff !important;">
                    <colgroup>
                        <col style="width:30%;"/>
                        <col style="width:20%;"/>
                        <col style="width:30%;"/>
                        <col style="width:20%;"/>
                    </colgroup>
                    <thead>
                        <tr style="background-color:#e9ecef !important; color:#111827 !important;">
                            <th style="border:1px solid #374151; padding:8px; text-align:left; color:#111827 !important; background-color:#e9ecef !important;">Basic Component</th>
                            <th style="border:1px solid #374151; padding:8px; text-align:right; color:#111827 !important; background-color:#e9ecef !important;">Basic Amount (INR)</th>
                            <th style="border:1px solid #374151; padding:8px; text-align:left; color:#111827 !important; background-color:#e9ecef !important;">Additional Component</th>
                            <th style="border:1px solid #374151; padding:8px; text-align:right; color:#111827 !important; background-color:#e9ecef !important;">Additional Amount (INR)</th>
                        </tr>
                    </thead>
                    <tbody>
                """

                for idx in range(total_rows):
                    left_name = ''
                    left_amount = ''
                    right_name = ''
                    right_amount = ''
                    left_style = ''
                    right_style = ''

                    if idx < len(left_rows):
                        left_name, left_val = left_rows[idx]
                        left_amount = f"{left_val:,.2f}"
                        if left_name == 'Gross Salary':
                            left_style = 'font-weight:bold; background-color:#f2f2f2;'

                    if idx < len(right_rows):
                        right_name, right_val = right_rows[idx]
                        right_amount = _fmt_amount(right_val)
                        if right_name == 'Net Salary':
                            right_style = 'font-weight:bold; background-color:#d4edda;'

                    html += f"""
                        <tr>
                            <td style="border:1px solid #374151; padding:6px; color:#111827 !important; background-color:#ffffff !important; {left_style}">{left_name}</td>
                            <td style="border:1px solid #374151; padding:6px; text-align:right; color:#111827 !important; background-color:#ffffff !important; {left_style}">{left_amount}</td>
                            <td style="border:1px solid #374151; padding:6px; color:#111827 !important; background-color:#ffffff !important; {right_style}">{right_name}</td>
                            <td style="border:1px solid #374151; padding:6px; text-align:right; color:#111827 !important; background-color:#ffffff !important; {right_style}">{right_amount}</td>
                        </tr>
                    """
                html += f"""
                    </tbody>
                </table>
                """
                payslip.payslip_calculation_html = html
            except Exception:
                payslip.payslip_calculation_html = False

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

    def _update_loan_ids_by_date_range(self):
        for rec in self:
            rec.loan_ids = [(5, 0, 0)]
            if not rec.employee_id or not rec.date_from or not rec.date_to:
                continue
            loan_lines = self.env['hr.loan.line'].search([
                ('employee_id', '=', rec.employee_id.id),
                ('paid', '=', False),
                ('date', '>=', rec.date_from),
                ('date', '<=', rec.date_to),
            ])
            rec.loan_ids = [(6, 0, loan_lines.ids)]

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
        self._update_loan_ids_by_date_range()
        self._compute_get_days_calculation_data()


    def action_compute_sheet(self):
        for rec in self:
            rec._compute_get_days_calculation_data()
        return super().action_compute_sheet()

    def action_create_journal_entry(self):
        if not self.env.user.has_group('account.group_account_user') and not self.env.user.has_group('account.group_account_manager'):
            raise UserError(_('Only Accounting users can create journal entries.'))

        payslips = self.filtered(lambda p: p.state == 'done')
        if not payslips:
            raise UserError(_('Please select confirmed payslips to create journal entries.'))

        action = self.env.ref('hrms_changes.action_hr_payslip_journal_entry_wizard').read()[0]
        action['context'] = {
            'active_model': 'hr.payslip',
            'active_ids': payslips.ids,
        }
        return action

    def action_open_send_payslip_mail_wizard(self):
        self.ensure_one()
        if not self.employee_id:
            raise UserError(_('Employee is required to send payslip email.'))

        partner = self.employee_id.work_contact_id or self.employee_id.address_home_id
        email_to = self.employee_id.work_email or (partner.email if partner else False)
        if not partner and not email_to:
            raise UserError(_('Please set Work Email or Home Address Email on employee to send payslip email.'))

        compose_form = self.env.ref('mail.email_compose_message_wizard_form')
        attachment = self._get_or_create_payslip_pdf_attachment()
        from_date_str = fields.Date.to_date(self.date_from).strftime('%d-%m-%Y') if self.date_from else ''
        to_date_str = fields.Date.to_date(self.date_to).strftime('%d-%m-%Y') if self.date_to else ''
        subject = _('Payslip - %s (%s to %s)') % (
            self.employee_id.name or '',
            from_date_str,
            to_date_str,
        )
        body_html = _(
            '<p>Dear %s,</p>'
            '<p>Please find attached your payslip for the period <strong>%s</strong> to <strong>%s</strong>.</p>'
            '<p>Regards,<br/>%s</p>'
        ) % (
            self.employee_id.name or '',
            from_date_str,
            to_date_str,
            self.env.user.name or '',
        )

        ctx = {
            'default_model': 'hr.payslip',
            'default_res_ids': [self.id],
            'default_composition_mode': 'comment',
            'default_use_template': False,
            'default_template_id': False,
            'default_partner_ids': [(6, 0, [partner.id])] if partner else False,
            'default_email_to': email_to or False,
            'default_subject': subject,
            'default_body': body_html,
            'default_attachment_ids': [(6, 0, [attachment.id])] if attachment else False,
            'default_email_layout_xmlid': 'mail.mail_notification_layout_with_responsible_signature',
            'force_email': True,
            'active_model': 'hr.payslip',
            'active_id': self.id,
            'active_ids': [self.id],
        }

        return {
            'name': _('Send Payslip'),
            'type': 'ir.actions.act_window',
            'res_model': 'mail.compose.message',
            'view_mode': 'form',
            'views': [(compose_form.id, 'form')],
            'target': 'new',
            'context': ctx,
        }

    def _get_or_create_payslip_pdf_attachment(self):
        self.ensure_one()

        file_name = (self.number or self.name or f'Payslip-{self.id}').replace('/', '_') + '.pdf'
        existing = self.env['ir.attachment'].search([
            ('res_model', '=', 'hr.payslip'),
            ('res_id', '=', self.id),
            ('name', '=', file_name),
            ('mimetype', '=', 'application/pdf'),
        ], limit=1)
        if existing:
            return existing

        pdf_content = False
        report_service = self.env['ir.actions.report'].sudo()
        for report_ref in ('hr_payroll_community.report_payslipdetails', 'hr_payroll_community.report_payslip'):
            try:
                pdf_content, _ = report_service._render_qweb_pdf(report_ref, self.id)
                if pdf_content:
                    break
            except Exception:
                pdf_content = False

        if not pdf_content:
            raise UserError(_('Payslip PDF report action is missing or inaccessible. Please reinstall/upgrade hr_payroll_community.'))

        return self.env['ir.attachment'].sudo().create({
            'name': file_name,
            'type': 'binary',
            'datas': base64.b64encode(pdf_content),
            'mimetype': 'application/pdf',
            'res_model': 'hr.payslip',
            'res_id': self.id,
        })

    def action_view_journal_entry(self):
        self.ensure_one()
        if not self.journal_entry_id:
            raise UserError(_('No journal entry has been created for this payslip yet.'))

        return {
            'name': _('Journal Entry'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.journal_entry_id.id,
            'target': 'current',
        }

    def action_payslip_done(self):
        res = super().action_payslip_done()
        for rec in self:
            if rec.loan_ids:
                rec.loan_ids.write({'paid': True})
                rec.salary_advance_ids.write({'paid': True})
        return res

    def action_payslip_draft(self):
        res = super().action_payslip_draft()
        for rec in self:
            if rec.loan_ids:
                rec.loan_ids.write({'paid': False})
                rec.salary_advance_ids.write({'paid': False})
        return res

    def _cancel_and_delete_journal_entry(self):
        for rec in self:
            move = rec.journal_entry_id.sudo()
            if not move:
                continue

            if move.state == 'posted':
                try:
                    move.button_draft()
                except Exception as err:
                    raise UserError(
                        _('Please cancel/reset journal entry %s to draft before payslip cancel.\n%s')
                        % (move.display_name, err)
                    )

            if move.state != 'draft':
                raise UserError(
                    _('Journal entry %s must be in draft before deletion.')
                    % move.display_name
                )

            try:
                move.unlink()
            except Exception as err:
                raise UserError(
                    _('Unable to delete journal entry %s.\n%s')
                    % (move.display_name, err)
                )

            rec.journal_entry_id = False

    def action_payslip_cancel(self):
        self._cancel_and_delete_journal_entry()
        res = super().action_payslip_cancel()
        for rec in self:
            if rec.loan_ids:
                rec.loan_ids.write({'paid': False})
                rec.salary_advance_ids.write({'paid': False})
        return res

    def unlink(self):
        for rec in self:
            if rec.state != 'cancel':
                raise UserError(_('Please cancel the payslip before deleting it.'))

        self._cancel_and_delete_journal_entry()
        return super().unlink()

    @api.onchange('date_from')
    def onchange_date_from(self):
        if self.date_from:
            self.date_to = self.date_from + relativedelta(months=+1, day=1, days=-1)
        worked_days_line_ids = self.get_worked_day_lines(self.contract_id, self.date_from,
                                                         self.date_to)
        worked_days_lines = self.worked_days_line_ids.browse([])
        for r in worked_days_line_ids:
            worked_days_lines += worked_days_lines.new(r)
        self._update_loan_ids_by_date_range()
        self._compute_get_days_calculation_data()
        return

    @api.onchange('date_to')
    def onchange_date_to(self):
        self._update_loan_ids_by_date_range()
        self._compute_get_days_calculation_data()
        return




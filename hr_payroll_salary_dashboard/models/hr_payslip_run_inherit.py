import io

import xlsxwriter

from odoo import models


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    def action_open_salary_dashboard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/hr_payroll_salary_dashboard/salary_dashboard/%s' % self.id,
            'target': 'new',
        }

    def _get_salary_dashboard_employee_code(self, employee):
        return employee.identification_id or str(employee.id)

    def _get_salary_dashboard_employee_type_label(self, employee):
        if not employee.employee_type:
            return ''
        selection = dict(employee.fields_get(['employee_type'])['employee_type']['selection'])
        return selection.get(employee.employee_type, '')

    def _get_salary_dashboard_lines(self):
        self.ensure_one()
        rows = []
        earning_names = []
        deduction_names = []
        paid_leave_names = []
        unpaid_leave_names = []

        for index, slip in enumerate(self.slip_ids.sorted(key=lambda s: s.employee_id.name or ''), start=1):
            employee = slip.employee_id
            calc_data = slip._prepare_salary_calculation_data() or {}
            summary = calc_data.get('summary') or slip.compute_days_summary()
            earnings = {name: amount for name, amount in calc_data.get('earning_rows', [])}
            deductions = {name: amount for name, amount in calc_data.get('right_rows', [])}
            paid_leaves = {d['name']: d['days'] for d in summary.get('paid_leaves', [])}
            unpaid_leaves = {d['name']: d['days'] for d in summary.get('unpaid_leaves', [])}

            for name in earnings:
                if name not in earning_names:
                    earning_names.append(name)
            for name in deductions:
                if name not in deduction_names:
                    deduction_names.append(name)
            for name in paid_leaves:
                if name not in paid_leave_names:
                    paid_leave_names.append(name)
            for name in unpaid_leaves:
                if name not in unpaid_leave_names:
                    unpaid_leave_names.append(name)

            bank_account = employee.primary_bank_account_id
            lop_day = summary.get('lop_day', 0.0) or 0.0
            effective_total_days = summary.get('effective_total_days', 0.0) or 0.0

            rows.append({
                'sno': index,
                'slip_id': slip.id,
                'employee_code': self._get_salary_dashboard_employee_code(employee),
                'employee_name': employee.name,
                'department': employee.department_id.name or '',
                'location': employee.work_location_name or '',
                'doj': employee.first_joining_date,
                'doe': employee.departure_date,
                'employee_type': self._get_salary_dashboard_employee_type_label(employee),
                'bank_name': bank_account.bank_id.name or '',
                'account_number': bank_account.acc_number or '',
                'earnings': earnings,
                'gross': slip.gross_salary,
                'hol': summary.get('public_holidays_days', 0.0) or 0.0,
                'paid_leaves': paid_leaves,
                'unpaid_leaves': unpaid_leaves,
                'lop': lop_day,
                'worked_days': effective_total_days - lop_day,
                'deductions': deductions,
                'total_deductions': slip.gross_salary - slip.net_salary,
                'net': slip.net_salary,
            })

        # Only keep dynamic columns that have at least one non-zero value
        # across the batch - an always-zero column (a salary component or
        # leave type unused by anyone in this run) is just noise.
        def _kept(names, dict_key):
            return [n for n in names if any(row[dict_key].get(n, 0.0) for row in rows)]

        return {
            'rows': rows,
            'earning_columns': _kept(earning_names, 'earnings'),
            'paid_leave_columns': _kept(paid_leave_names, 'paid_leaves'),
            'unpaid_leave_columns': _kept(unpaid_leave_names, 'unpaid_leaves'),
            'deduction_columns': _kept(deduction_names, 'deductions'),
            'show_hol': any(row['hol'] for row in rows),
            'show_lop': any(row['lop'] for row in rows),
        }

    @staticmethod
    def _sd_dict_getter(dict_key, name):
        # A plain closure defined inside the building loop would capture
        # `name` by reference, so every column ends up reading the last
        # loop value - binding it as a default arg here freezes it instead.
        return lambda row: row[dict_key].get(name, 0.0)

    def _get_salary_dashboard_xlsx(self):
        self.ensure_one()
        payload = self._get_salary_dashboard_lines()
        rows = payload['rows']

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        header_format = workbook.add_format({
            'bold': True, 'bg_color': '#F1F1F1', 'border': 1, 'align': 'center', 'valign': 'vcenter',
        })
        text_format = workbook.add_format({'border': 1})
        date_format = workbook.add_format({'border': 1, 'num_format': 'dd-mm-yyyy'})
        amount_format = workbook.add_format({'border': 1, 'num_format': '#,##0.00'})
        days_format = workbook.add_format({'border': 1, 'num_format': '0.0'})
        bold_text_format = workbook.add_format({'bold': True, 'border': 1, 'bg_color': '#F8F8F8'})
        bold_amount_format = workbook.add_format({
            'bold': True, 'border': 1, 'bg_color': '#F8F8F8', 'num_format': '#,##0.00',
        })
        bold_days_format = workbook.add_format({
            'bold': True, 'border': 1, 'bg_color': '#F8F8F8', 'num_format': '0.0',
        })

        columns = [
            ('employee_code', 'Emp Code', text_format, 12, lambda r: r['employee_code']),
            ('employee_name', 'Name', text_format, 22, lambda r: r['employee_name']),
            ('department', 'Department', text_format, 18, lambda r: r['department']),
            ('location', 'Location', text_format, 14, lambda r: r['location']),
            ('doj', 'DOJ', date_format, 12, lambda r: r['doj']),
            ('doe', 'DOE', date_format, 12, lambda r: r['doe']),
            ('employee_type', 'Type', text_format, 10, lambda r: r['employee_type']),
            ('bank_name', 'Bank Name', text_format, 18, lambda r: r['bank_name']),
            ('account_number', 'Account Number', text_format, 18, lambda r: r['account_number']),
        ]
        for name in payload['earning_columns']:
            columns.append((name, name, amount_format, 12, self._sd_dict_getter('earnings', name)))
        columns.append(('gross', 'Gross', amount_format, 12, lambda r: r['gross']))
        if payload['show_hol']:
            columns.append(('hol', 'HOL', days_format, 8, lambda r: r['hol']))
        for name in payload['paid_leave_columns']:
            columns.append((name, name, days_format, 10, self._sd_dict_getter('paid_leaves', name)))
        for name in payload['unpaid_leave_columns']:
            columns.append((name, '%s (Unpaid)' % name, days_format, 14, self._sd_dict_getter('unpaid_leaves', name)))
        if payload['show_lop']:
            columns.append(('lop', 'LOP', days_format, 8, lambda r: r['lop']))
        columns.append(('worked_days', 'Worked Days', days_format, 12, lambda r: r['worked_days']))
        for name in payload['deduction_columns']:
            columns.append((name, name, amount_format, 14, self._sd_dict_getter('deductions', name)))
        columns.append(('total_deductions', 'Total Deductions', amount_format, 16, lambda r: r['total_deductions']))
        columns.append(('net', 'Net Amount', amount_format, 14, lambda r: r['net']))

        sheet = workbook.add_worksheet((self.name or 'Salary Dashboard')[:31])
        sheet.write(0, 0, 'S.No', header_format)
        sheet.set_column(0, 0, 6)
        for col_idx, (key, label, fmt, width, getter) in enumerate(columns, start=1):
            sheet.write(0, col_idx, label, header_format)
            sheet.set_column(col_idx, col_idx, width)
        sheet.freeze_panes(1, 3)

        for row_idx, row in enumerate(rows, start=1):
            sheet.write(row_idx, 0, row['sno'], text_format)
            for col_idx, (key, label, fmt, width, getter) in enumerate(columns, start=1):
                value = getter(row)
                sheet.write(row_idx, col_idx, value if value not in (None, False) else '', fmt)

        total_row = len(rows) + 1
        sheet.write(total_row, 1, 'Total', bold_text_format)
        for col_idx, (key, label, fmt, width, getter) in enumerate(columns, start=1):
            if fmt not in (amount_format, days_format):
                continue
            total_value = sum((getter(row) or 0) for row in rows)
            sheet.write(total_row, col_idx, total_value, bold_amount_format if fmt is amount_format else bold_days_format)

        workbook.close()
        return output.getvalue()

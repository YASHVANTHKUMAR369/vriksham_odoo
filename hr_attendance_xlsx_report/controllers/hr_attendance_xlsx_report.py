from odoo import http
from odoo.http import request, content_disposition
import io
from dateutil.rrule import rrule, DAILY

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter


class EmployeeAttendanceXlsxController(http.Controller):

    @http.route('/employee_attendance/xlsx/<int:wizard_id>',
                type='http', auth='user', csrf=False)
    def export_employee_attendance_xlsx(self, wizard_id, **kwargs):

        wizard = request.env['employee.attendance.report'].sudo().browse(wizard_id)
        from_date = wizard.from_date
        to_date = wizard.to_date
        company = wizard.company_id.id

        # ---------------------------------------------------------
        # PUBLIC HOLIDAYS
        # ---------------------------------------------------------
        public_holidays = request.env['resource.calendar.leaves'].sudo().search([
            ('date_from', '<=', to_date),
            ('date_to', '>=', from_date),
            ('resource_id', '=', False),
        ])

        holiday_dates = set()
        for ph in public_holidays:
            for d in rrule(DAILY, dtstart=ph.date_from.date(), until=ph.date_to.date()):
                holiday_dates.add(d.date())

        # ---------------------------------------------------------
        # ATTENDANCE SQL
        # ---------------------------------------------------------
        query = """
            SELECT
                hr_e.id AS emp_id,
                DATE(hr_at.check_in) AS att_date,
                MIN(hr_at.check_in) AS in_time,
                MAX(hr_at.check_out) AS out_time,
                EXTRACT(EPOCH FROM (MAX(hr_at.check_out) - MIN(hr_at.check_in))) / 3600 AS hours
            FROM hr_attendance hr_at
            JOIN hr_employee hr_e ON hr_at.employee_id = hr_e.id
            WHERE DATE(hr_at.check_in) BETWEEN %s AND %s
                AND hr_e.company_id = %s
            GROUP BY hr_e.id, DATE(hr_at.check_in)
        """
        request.env.cr.execute(query, (from_date, to_date, company))
        rows = request.env.cr.dictfetchall()

        # ---------------------------------------------------------
        # MAP EMPLOYEE → DATE → DATA
        # ---------------------------------------------------------
        emp_map = {}
        for r in rows:
            emp_map.setdefault(r['emp_id'], {})[r['att_date']] = r

        calendar = request.env.ref('resource.resource_calendar_std')
        shift_hours = calendar.hours_per_day
        date_range = list(rrule(DAILY, dtstart=from_date, until=to_date))

        # ---------------------------------------------------------
        # SUMMARY
        # ---------------------------------------------------------
        summary = {}
        for emp_id, recs in emp_map.items():
            present = absent = 0
            for d in date_range:
                if d.weekday() == 6 or d.date() in holiday_dates:
                    continue

                hours = recs.get(d.date(), {}).get('hours', 0)
                if hours >= 1:
                    present += 1
                else:
                    absent += 1

            summary[emp_id] = {
                'working_days': present + absent,
                'present_days': present,
                'absent_days': absent,
            }

        # ---------------------------------------------------------
        # XLSX
        # ---------------------------------------------------------
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Attendance')

        # FORMATS
        header = workbook.add_format({'bold': True, 'border': 1, 'align': 'center', 'valign': 'vcenter', 'text_wrap':True})
        border = workbook.add_format({'border': 1, 'align': 'center'})
        green = workbook.add_format({'bg_color': '#28A828', 'border': 1})
        rose = workbook.add_format({'bg_color': '#DA70D6', 'border': 1})
        red = workbook.add_format({'bg_color': '#E74C3C', 'border': 1})
        yellow = workbook.add_format({'bg_color': '#F1C40F', 'border': 1})
        blue = workbook.add_format({'bg_color': '#5DADE2', 'border': 1})
        title = workbook.add_format({'bold': True, 'font_size': 22, 'align': 'center'})

        # TITLE
        sheet.merge_range('A2:AN2', 'Attendance Report', title)
        sheet.write('B6:C6', f'From Date: {from_date}')
        sheet.write('B7:C7', f'To Date: {to_date}')
        sheet.write('B8:C9', f'Company: {wizard.company_id.name}')

        # LEGEND
        sheet.write('AO3', '', green);  sheet.write('BB3', 'Full Day')
        sheet.write('AO4', '', rose);   sheet.write('BB4', 'Half Day')
        sheet.write('AO5', '', red);    sheet.write('BB5', 'Absent')
        sheet.write('AO6', '', yellow); sheet.write('BB6', 'Sunday')
        sheet.write('AO7', '', blue);   sheet.write('BB7', 'Public Holiday')

        # ---------------------------------------------------------
        # HEADERS
        # ---------------------------------------------------------
        row = 9
        col = 0

        fixed_headers = [
            'Sl No', 'Employee Name', 'Employee ID',
            'Department', 'Designation', 'Shift'
        ]

        for h in fixed_headers:
            sheet.write(row, col, h, header)
            col += 1

        date_col_start = col
        for d in date_range:
            sheet.write(row, col, d.strftime('%d-%m-%Y'), header)
            col += 1

        for h in ['Total Working Days', 'Present Days', 'Absent Days', 'OT']:
            sheet.write(row, col, h, header)
            col += 1

        # ---------------------------------------------------------
        # DATA ROWS
        # ---------------------------------------------------------
        r = row + 1
        sl = 1

        # employees = request.env['hr.employee'].sudo().search([], order='name')
        domain = [('company_id', '=', wizard.company_id.id)]

        if wizard.employee_ids:
            domain.append(('id', 'in', wizard.employee_ids.ids))

        if wizard.emp_code:
            domain.append(('identification_id', '=', wizard.emp_code))

        employees = request.env['hr.employee'].sudo().search(domain, order='name')

        for emp in employees:
            recs = emp_map.get(emp.id, {})
            summ = summary.get(emp.id, {'working_days': 0, 'present_days': 0, 'absent_days': 0, 'overtime_hours': 0})

            sheet.write_row(r, 0, [
                sl,
                emp.name,
                emp.identification_id,
                emp.department_id.name if emp.department_id else '',
                emp.job_id.name if emp.job_id else '',
                emp.resource_calendar_id.name if emp.resource_calendar_id else '',
            ], border)
            overtime = 0.0
            for att in emp.attendance_ids:
                overtime += att.overtime_hours

            c = date_col_start
            for d in date_range:
                if d.weekday() == 6:
                    sheet.write(r, c, 'SUN', yellow)

                elif d.date() in holiday_dates:
                    sheet.write(r, c, 'PH', blue)

                else:
                    hours = round(recs.get(d.date(), {}).get('hours', 0) or 0, 2)

                    if hours >= shift_hours:
                        sheet.write(r, c, hours, green)
                    elif hours >= 1:
                        sheet.write(r, c, hours, rose)
                    else:
                        sheet.write(r, c, hours, red)

                c += 1

            sheet.write_row(r, c, [
                summ['working_days'],
                summ['present_days'],
                summ['absent_days'],
                overtime,

            ], border)

            r += 1
            sl += 1

        workbook.close()
        output.seek(0)

        filename = f"Attendance_Report_{from_date}_to_{to_date}.xlsx"
        return request.make_response(
            output.read(),
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', content_disposition(filename)),
            ]
        )

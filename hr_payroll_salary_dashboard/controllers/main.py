from odoo import http
from odoo.http import content_disposition, request


class HrPayrollSalaryDashboardController(http.Controller):

    @http.route('/hr_payroll_salary_dashboard/salary_dashboard/<int:run_id>', type='http', auth='user')
    def salary_dashboard_html(self, run_id, **kwargs):
        run = request.env['hr.payslip.run'].browse(run_id)
        run.check_access('read')
        payload = run._get_salary_dashboard_lines()
        html = request.env['ir.qweb']._render('hr_payroll_salary_dashboard.salary_dashboard_html_template', {
            'run': run,
            **payload,
        })
        return request.make_response(html, headers=[('Content-Type', 'text/html')])

    @http.route('/hr_payroll_salary_dashboard/salary_dashboard_xlsx/<int:run_id>', type='http', auth='user')
    def salary_dashboard_xlsx(self, run_id, **kwargs):
        run = request.env['hr.payslip.run'].browse(run_id)
        run.check_access('read')
        content = run._get_salary_dashboard_xlsx()
        filename = "%s.xlsx" % (run.name or 'Salary Dashboard')
        headers = [
            ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
            ('Content-Length', len(content)),
            ('Content-Disposition', content_disposition(filename)),
        ]
        return request.make_response(content, headers=headers)

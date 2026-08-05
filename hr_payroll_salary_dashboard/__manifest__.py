{
    'name': 'HR Payroll Salary Dashboard',
    'version': '19.0.1.0.0',
    'summary': 'Spreadsheet-style salary dashboard for payslip batches, with Excel export',
    'depends': ['hr_payroll_community', 'hrms_changes'],
    'data': [
        'views/salary_dashboard_template.xml',
        'views/hr_payslip_run_view_inherit.xml',
    ],
    'author': 'yash',
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}

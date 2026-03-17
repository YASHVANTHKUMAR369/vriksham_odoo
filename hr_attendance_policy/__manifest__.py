{
    'name': 'HR Attendance Policy',
    'version': '1.0',
    'category': 'Human Resources',
    'summary': 'Company Attendance Rules & Approval Workflow',
    'depends': ['hr_attendance', 'hr_holidays', 'hr_payroll_community'],
    'data': [
        'security/ir.model.access.csv',
        'data/attendance_cron.xml',
        'views/hr_attendance_view.xml',
        # 'views/employee_movement_view.xml',
    ],
    'author': 'icore',
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}

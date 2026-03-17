{
    'name': 'Custom Leave Rules (CL & EL)',
    'version': '1.0',
    'category': 'HR',
    'summary': 'Custom Casual Leave and Earned Leave without hr.leave',
    'depends': ['hr', 'hr_holidays', 'hr_holidays_attendance'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'views/leave_request_view.xml',
        'views/leave_menu.xml',
        'views/hr_employee_views.xml'
    ],
    'installable': True,
    'application': False,
}
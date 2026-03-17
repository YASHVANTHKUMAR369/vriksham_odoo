{
    'name': "Employee Attendance Xlsx Report",
    'version': '19.0.1.0.0',
    'category': 'Human Resources',
    'summary': """This module will manage  the attendance report of employees 
    in xlsx""",
    'description': """This module helps to generate the attendance report of 
    employees in the XLSX format""",
    'author': 'ICore',
    'company': 'ICore',
    'maintainer': 'ICore',
    'depends': ['hr_attendance'],
    'data': [
        'security/ir.model.access.csv',
        'wizards/employee_attendance_report_views.xml',
        'views/hr_attendance.xml'
    ],
    'assets': {
        'web.assets_backend': [
            # 'hr_attendance_xlsx_report/static/src/js/action_manager.js',
        ]
    },
    'images': ['static/description/banner.jpg'],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False
}

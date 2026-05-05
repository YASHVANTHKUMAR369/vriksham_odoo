# -*- coding: utf-8 -*-
{
    'name': 'HR Attendance Own Access',
    'version': '19.0.1.0.0',
    'summary': 'Adds "Own Attendance Only" role in attendance access rights',
    'category': 'Human Resources',
    'author': 'Custom',
    'license': 'LGPL-3',
    'depends': ['hr_attendance'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/hr_attendance_views.xml',
        'views/hr_attendance_menu_access.xml',
    ],
    'installable': True,
    'application': False,
}

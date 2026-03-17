{
    'name': 'Dynavac Biometric Attendance',
    'version': '19.0.1.0.0',
    'depends': ['base', 'hr_attendance', 'hr'],
    'data': [
        'data/ir_cron_data.xml',
        'security/ir.model.access.csv',
        'views/biometric_log_views.xml',
        'views/res_config_settings_views.xml',
        'views/hr_attendance_inherit.xml',
        'views/menu.xml',

    ],
    'author': 'yash',
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}

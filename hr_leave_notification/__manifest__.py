{
    'name': 'HR Leave Notification',
    'version': '19.0.1.0.0',
    'summary': 'Send email and notification to Time Off officer when employee creates a leave request',
    'category': 'Human Resources/Time Off',
    'depends': ['hr_holidays'],
    'data': [
        'security/ir.model.access.csv',
        'data/mail_template.xml',
    ],
    'author': 'yash',
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}

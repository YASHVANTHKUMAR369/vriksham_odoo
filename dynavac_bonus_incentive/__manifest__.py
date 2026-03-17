{
    'name': 'Dynavac Bonus and Incentive',
    'version': '19.0.1.0.0',
    'depends': ['base', 'hr','ohrms_loan'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/employee_bonus.xml',
        'views/employee_incentive.xml',
    ],
    'author': 'santhiya',
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}

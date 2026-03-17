{
    'name': "Payroll Report",
    'version': '19.0.1.0.0',
    'category': 'Payroll',
    'summary': """ This module will used to print payslip reoprt in xlsx """,
    'description': """This module helps to generate employees payslip report in xlsx""",
    'author': 'ICore',
    'company': 'ICore',
    'maintainer': 'ICore',
    'depends': ['hr_payroll_community'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/report.xml',
        'wizard/payslip_report_wizard.xml',
    ],
    'assets': {
        'web.assets_backend': [
        ]
    },
    'images': ['static/description/banner.jpg'],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False
}

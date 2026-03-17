# -*- coding: utf-8 -*-
{
    'name': "payroll_icore",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Long description of module's purpose
    """,

    'author': "Icore Software Technologies",
    'website': "https://www.icore.net.in",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.2',

    # any module necessary for this one to work correctly
    'depends': ['hr_payroll_community', 'hr_attendance', 'hr_holidays','sale','hr'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/hr_payslip_view.xml',
	#'views/sale_order_views.xml'
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}


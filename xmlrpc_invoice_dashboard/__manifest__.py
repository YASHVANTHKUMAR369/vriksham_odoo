# -*- coding: utf-8 -*-
{
    'name': 'XML-RPC Invoice Dashboard',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Fetch invoice data from a remote Odoo over XML-RPC and print it as a GST invoice PDF',
    'description': """
XML-RPC Invoice Dashboard
==========================
- Settings to configure the remote Odoo URL, database, username and password.
- A dashboard where you type an invoice number and fetch its data from that
  remote Odoo through the XML-RPC API, shown as JSON.
- A Print button that renders the fetched data as a GST invoice PDF.
""",
    'author': 'Vriksham Softech',
    'website': 'https://vrikshamsofttech.com',
    'license': 'LGPL-3',
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'report/paperformat.xml',
        'report/report_templates.xml',
        'report/report_actions.xml',
        'views/invoice_xmlrpc_dashboard_views.xml',
        'views/res_config_settings_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': True,
}

# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    xmlrpc_odoo_url = fields.Char(
        string="Odoo URL",
        config_parameter='xmlrpc_invoice_dashboard.odoo_url',
        help="Base URL of the Odoo server to fetch invoices from, e.g. https://mycompany.odoo.com",
    )
    xmlrpc_odoo_db = fields.Char(
        string="Database",
        config_parameter='xmlrpc_invoice_dashboard.odoo_db',
        help="Name of the database on that server.",
    )
    xmlrpc_odoo_username = fields.Char(
        string="Username",
        config_parameter='xmlrpc_invoice_dashboard.odoo_username',
        help="Login used to authenticate on that server.",
    )
    xmlrpc_odoo_password = fields.Char(
        string="Password / API Key",
        config_parameter='xmlrpc_invoice_dashboard.odoo_password',
        help="Password or API key for that login.",
    )
    xmlrpc_invoice_signature = fields.Binary(
        related='company_id.xmlrpc_invoice_signature',
        string="Authorized Signature",
        readonly=False,
        help="Signature image printed above 'Authorized signatory' on the printed GST invoice.",
    )

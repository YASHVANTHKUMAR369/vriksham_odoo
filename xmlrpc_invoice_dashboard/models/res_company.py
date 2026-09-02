# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    xmlrpc_invoice_signature = fields.Binary(
        string="Authorized Signature",
        help="Signature image printed above 'Authorized signatory' on the "
             "GST invoice PDF printed from the Invoice XML-RPC dashboard.",
    )

from odoo import fields, models


class AccountMoveInherit(models.Model):
    _inherit = "account.move"

    bill_date = fields.Date(string="Bill Date")
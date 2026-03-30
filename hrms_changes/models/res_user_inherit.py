from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    sign_signature = fields.Binary(string="Signature", attachment=True,
                                   help="User signature image (used in reports and documents)")


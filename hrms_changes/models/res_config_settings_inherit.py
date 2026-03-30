from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    hr_name = fields.Char(
        string='HR Name',
        related='company_id.hr_name',
        readonly=False,
    )

    hr_signature = fields.Image(
        string='HR Signature',
        related='company_id.hr_signature',
        readonly=False,
    )
    l10n_in_gsp = fields.Char()

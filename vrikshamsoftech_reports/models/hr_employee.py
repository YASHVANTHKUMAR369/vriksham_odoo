from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    def action_offer_letter(self):
        return self.env.ref('vrikshamsoftech_reports.vriksham_action_record_offer_letter').report_action(self)

    x_offer_letter_contract = fields.Many2one(
        'hr.version',
        string='Offer Letter Contract',
        help='Contract associated with the offer letter'
    )
    x_date_of_joining = fields.Date(
        string='Date of Joining',
        help='Expected date of joining for the employee'
    )
    x_hike_contract = fields.Many2one(
        'hr.version',
        string='Hike Contract',
        help='Contract associated with the hike/increment letter'
    )
    x_appreciation_project = fields.Char(
        string='Appreciation Project',
        help='Project name for appreciation letter'
    )
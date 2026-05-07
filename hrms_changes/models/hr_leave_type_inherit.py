from odoo import models


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    def _get_leaves_on_public_holiday(self):
        leaves = super()._get_leaves_on_public_holiday()
        return leaves.filtered(lambda l: not l.holiday_status_id.include_public_holidays_in_duration)

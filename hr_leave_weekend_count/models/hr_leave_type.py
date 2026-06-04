from odoo import fields, models


class HrLeaveType(models.Model):
    _inherit = "hr.leave.type"

    count_weekend_days = fields.Boolean(
        string="Count Weekend Days",
        default=False,
        help="When enabled, Saturday and Sunday are included in the leave "
             "duration calculation. By default, weekends are excluded because "
             "they are not part of the employee's working schedule.",
    )

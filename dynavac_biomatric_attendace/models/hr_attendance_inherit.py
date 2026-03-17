from odoo import fields, models, api


class HrAttendance(models.Model):
    """Inherit the model to add fields"""
    _inherit = 'hr.attendance'

    attendance_mode = fields.Selection(
        selection=[('biometric', "Biometric"),
                   ('manual', "Manual"), ], default='manual', readonly=True
    )

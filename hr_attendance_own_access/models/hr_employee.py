from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    attendance_manager_id = fields.Many2one(
        "res.users",
        store=True,
        readonly=False,
        string="Attendance Approver",
        domain="[('share', '=', False), ('company_ids', 'in', company_id)]",
        groups="hr_attendance.group_hr_attendance_officer,hr_attendance_own_access.group_hr_attendance_own",
        help="The user set in Attendance will access the attendance of the employee through the dedicated app and will be able to edit them.",
    )

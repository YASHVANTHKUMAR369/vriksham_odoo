from odoo import api, models


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        # For custom own-attendance role, prefill employee with current user's employee.
        if "employee_id" in fields_list and not values.get("employee_id"):
            if self.env.user.has_group("hr_attendance_own_access.group_hr_attendance_own") and self.env.user.employee_id:
                values["employee_id"] = self.env.user.employee_id.id
        return values

    @api.depends("employee_id", "check_in", "check_out")
    def _compute_is_manager(self):
        """Compute manager flag without triggering access errors for own-access users.

        Core logic reads employee.attendance_manager_id, which is restricted to
        officer group. For own-access users, use sudo only for that manager-id
        lookup while keeping the same boolean outcome.
        """
        have_manager_right = self.env.user.has_group("hr_attendance.group_hr_attendance_user")
        have_officer_right = self.env.user.has_group("hr_attendance.group_hr_attendance_officer")
        current_user_id = self.env.user.id

        for attendance in self:
            manager_user_id = attendance.employee_id.sudo().attendance_manager_id.id
            attendance.is_manager = have_manager_right or (
                have_officer_right and manager_user_id == current_user_id
            )

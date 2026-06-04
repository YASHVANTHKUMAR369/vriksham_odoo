from datetime import datetime, time, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class HrAttendanceMassCreateWizard(models.TransientModel):
    _name = "hr.attendance.mass.create.wizard"
    _description = "Mass Create Employee Attendances"

    checkin_time = fields.Float(
        string="Check In Time",
        default=9.0,
        required=True,
        help="Check-in time as float hours (example: 9.5 = 09:30).",
    )
    checkout_time = fields.Float(
        string="Check Out Time",
        default=18.0,
        required=True,
        help="Check-out time as float hours (example: 18.0 = 18:00).",
    )
    no_attendance_create_employee_ids = fields.Many2many(
        "hr.employee",
        string="Employees To Skip",
        help="Selected employees will be excluded from attendance creation.",
    )
    saturday = fields.Boolean(string="Include Saturday")
    sunday = fields.Boolean(string="Include Sunday")
    date_from = fields.Date(string="Date From", required=True, default=fields.Date.context_today)
    date_to = fields.Date(string="Date To", required=True, default=fields.Date.context_today)

    @api.constrains("date_from", "date_to")
    def _check_date_range(self):
        for wizard in self:
            if wizard.date_from and wizard.date_to and wizard.date_to < wizard.date_from:
                raise ValidationError(_("Date To must be greater than or equal to Date From."))

    @api.constrains("checkin_time", "checkout_time")
    def _check_times(self):
        for wizard in self:
            if wizard.checkin_time < 0 or wizard.checkin_time >= 24:
                raise ValidationError(_("Check In Time must be between 0.0 and 24.0."))
            if wizard.checkout_time <= 0 or wizard.checkout_time > 24:
                raise ValidationError(_("Check Out Time must be between 0.0 and 24.0."))
            if wizard.checkout_time <= wizard.checkin_time:
                raise ValidationError(_("Check Out Time must be greater than Check In Time."))

    @staticmethod
    def _float_to_time(float_hour):
        hours = int(float_hour)
        minutes = int(round((float_hour - hours) * 60))
        if minutes == 60:
            hours += 1
            minutes = 0
        if hours >= 24:
            hours = 23
            minutes = 59
        return time(hour=hours, minute=minutes)

    def _date_is_allowed(self, current_date):
        weekday = current_date.weekday()
        if weekday == 5 and not self.saturday:
            return False
        if weekday == 6 and not self.sunday:
            return False
        if weekday in (5, 6):
            return self.saturday if weekday == 5 else self.sunday
        return True

    def action_create_attendance(self):
        self.ensure_one()

        employees = self.env["hr.employee"].search([
            ("id", "not in", self.no_attendance_create_employee_ids.ids),
        ])
        if not employees:
            return {"type": "ir.actions.act_window_close"}

        checkin_t = self._float_to_time(self.checkin_time)
        checkout_t = self._float_to_time(self.checkout_time)

        attendance_values = []
        current_date = self.date_from

        while current_date <= self.date_to:
            if self._date_is_allowed(current_date):
                day_start = datetime.combine(current_date, time.min)
                day_end = datetime.combine(current_date, time.max)
                checkin_dt = fields.Datetime.to_string(datetime.combine(current_date, checkin_t))
                checkout_dt = fields.Datetime.to_string(datetime.combine(current_date, checkout_t))

                existing = self.env["hr.attendance"].search([
                    ("employee_id", "in", employees.ids),
                    ("check_in", ">=", fields.Datetime.to_string(day_start)),
                    ("check_in", "<=", fields.Datetime.to_string(day_end)),
                ])
                existing_employee_ids = set(existing.mapped("employee_id").ids)

                for employee in employees:
                    if employee.id in existing_employee_ids:
                        continue
                    attendance_values.append(
                        {
                            "employee_id": employee.id,
                            "check_in": checkin_dt,
                            "check_out": checkout_dt,
                        }
                    )

            current_date += timedelta(days=1)

        if attendance_values:
            self.env["hr.attendance"].create(attendance_values)

        return {"type": "ir.actions.act_window_close"}

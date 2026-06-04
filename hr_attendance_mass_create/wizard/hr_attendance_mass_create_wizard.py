from datetime import datetime, time, timedelta

import pytz

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

    def _get_user_tz(self):
        """Return the user's (or company's) pytz timezone, defaulting to UTC."""
        tz_name = (
            self.env.user.tz
            or self.env.company.partner_id.tz
            or "UTC"
        )
        try:
            return pytz.timezone(tz_name)
        except pytz.exceptions.UnknownTimeZoneError:
            return pytz.UTC

    def _local_dt_to_utc(self, naive_local_dt, tz):
        """Localize a naive datetime in *tz* and return a naive UTC datetime."""
        return tz.localize(naive_local_dt).astimezone(pytz.UTC).replace(tzinfo=None)

    def _get_effective_times(self, employee, current_date, checkin_float, checkout_float, tz):
        """
        Return (checkin_float, checkout_float) if no approved leave exists on
        *current_date* for *employee*, otherwise return None.
        Any leave (full-day, half-day, or hourly) blocks attendance creation.
        """
        # Leave date_from/date_to are stored in UTC; convert local day boundaries to UTC
        day_start_utc = self._local_dt_to_utc(datetime.combine(current_date, time.min), tz)
        day_end_utc = self._local_dt_to_utc(datetime.combine(current_date, time.max), tz)

        leave_exists = self.env["hr.leave"].search_count([
            ("employee_id", "=", employee.id),
            ("state", "in", ["validate", "validate1"]),
            ("date_from", "<=", fields.Datetime.to_string(day_end_utc)),
            ("date_to", ">=", fields.Datetime.to_string(day_start_utc)),
        ])

        if leave_exists:
            return None

        return (checkin_float, checkout_float)

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

        tz = self._get_user_tz()
        attendance_values = []
        current_date = self.date_from

        while current_date <= self.date_to:
            if self._date_is_allowed(current_date):
                # Attendance check_in is stored in UTC; convert day boundaries to UTC
                day_start_utc = self._local_dt_to_utc(datetime.combine(current_date, time.min), tz)
                day_end_utc = self._local_dt_to_utc(datetime.combine(current_date, time.max), tz)

                existing = self.env["hr.attendance"].search([
                    ("employee_id", "in", employees.ids),
                    ("check_in", ">=", fields.Datetime.to_string(day_start_utc)),
                    ("check_in", "<=", fields.Datetime.to_string(day_end_utc)),
                ])
                existing_employee_ids = set(existing.mapped("employee_id").ids)

                for employee in employees:
                    if employee.id in existing_employee_ids:
                        continue

                    # Compute effective times considering approved leaves
                    times = self._get_effective_times(
                        employee, current_date,
                        self.checkin_time, self.checkout_time, tz,
                    )
                    if times is None:
                        # Full-day leave or leave covers entire work window → skip
                        continue

                    eff_checkin_float, eff_checkout_float = times
                    # Convert local times to UTC before storing
                    checkin_utc = self._local_dt_to_utc(
                        datetime.combine(current_date, self._float_to_time(eff_checkin_float)), tz
                    )
                    checkout_utc = self._local_dt_to_utc(
                        datetime.combine(current_date, self._float_to_time(eff_checkout_float)), tz
                    )
                    attendance_values.append({
                        "employee_id": employee.id,
                        "check_in": fields.Datetime.to_string(checkin_utc),
                        "check_out": fields.Datetime.to_string(checkout_utc),
                    })

            current_date += timedelta(days=1)

        if attendance_values:
            self.env["hr.attendance"].create(attendance_values)

        return {"type": "ir.actions.act_window_close"}

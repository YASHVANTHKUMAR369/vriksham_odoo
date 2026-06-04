from datetime import timedelta
from math import ceil

from odoo import api, models
from odoo.addons.resource.models.utils import HOURS_PER_DAY


class HrLeave(models.Model):
    _inherit = "hr.leave"

    def _get_durations(self, check_leave_type=True, resource_calendar=None):
        result = super()._get_durations(
            check_leave_type=check_leave_type,
            resource_calendar=resource_calendar,
        )

        for leave in self:
            if not leave.holiday_status_id.count_weekend_days:
                continue
            if not leave.request_date_from or not leave.request_date_to:
                continue

            # Count Saturday (5) and Sunday (6) days in the requested date range
            weekend_days = 0
            current = leave.request_date_from
            while current <= leave.request_date_to:
                if current.weekday() in (5, 6):
                    weekend_days += 1
                current += timedelta(days=1)

            if not weekend_days:
                continue

            hours_per_day = (
                (resource_calendar or leave.resource_calendar_id).hours_per_day
                or HOURS_PER_DAY
            )
            current_days, current_hours = result.get(leave.id, (0, 0))
            new_days = current_days + weekend_days
            if check_leave_type and leave.leave_type_request_unit == "day":
                new_days = ceil(new_days)
            result[leave.id] = (new_days, current_hours + weekend_days * hours_per_day)

        return result

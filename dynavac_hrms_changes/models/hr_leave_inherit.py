from odoo import models, fields, api, _
from datetime import datetime, timedelta
from odoo.exceptions import ValidationError

class HrLeave(models.Model):
    _inherit = 'hr.leave'


    def get_actual_leave(self, from_date, to_date):
        self.ensure_one()
        value = 0

        leave_start = self.request_date_from
        leave_end = self.request_date_to

        # No overlap
        if to_date < leave_start or from_date > leave_end:
            return value

        # Overlapping period
        overlap_start = max(from_date, leave_start)
        overlap_end = min(to_date, leave_end)

        # Get working days from employee calendar
        week_days = list(set(
            self.employee_id.resource_calendar_id.attendance_ids.mapped('dayofweek')
        ))

        week_off_count = 0
        current_day = overlap_start

        while current_day <= overlap_end:
            if str(current_day.weekday()) not in week_days:
                week_off_count += 1
            current_day += timedelta(days=1)

        # Total overlapping days
        total_days = (overlap_end - overlap_start).days + 1

        # Actual leave excluding week offs
        value = total_days - week_off_count

        return value
    def _get_leave_type(self, holiday_status_id):
        return self.env['hr.leave.type'].search([('id', '=', holiday_status_id)], limit=1)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            print("==================", vals)
            holiday_status = self._get_leave_type(vals['holiday_status_id'])
            employee = self.env['hr.employee'].browse(vals['employee_id'])._get_remaining_leaves
            if holiday_status.code =="S-OFF":
                request_date = fields.Date.from_string(vals['request_date_from'])
                if request_date.weekday() != 5:
                    raise ValidationError(
                        _("You can only create this leave on Saturday.")
                    )
            if holiday_status.code =="PER":
                if  vals['request_hour_to'] - vals['request_hour_from'] > 1:
                    raise ValidationError(
                        _("You can only create this leave for exactly 1 hour.")
                    )

            if holiday_status.code in ["ML"]:
                date_from = fields.Date.from_string(vals['request_date_from'])
                date_to = fields.Date.from_string(vals['request_date_to'])

                total_days = (date_to - date_from).days + 1

                if total_days != 182:
                    expected_end_date = date_from + timedelta(days=181)

                    raise ValidationError(
                        _("For %s leave, the duration must be exactly 182 days.\n"
                          "If start date is %s, end date must be %s.")
                        % (holiday_status.name, date_from.strftime("%d-%m-%Y"), expected_end_date.strftime("%d-%m-%Y"))
                    )

            if holiday_status.code in ["PL"]:
                date_from = fields.Date.from_string(vals['request_date_from'])
                date_to = fields.Date.from_string(vals['request_date_to'])

                total_days = (date_to - date_from).days + 1

                if total_days != 3:
                    expected_end_date = date_from + timedelta(days=2)

                    raise ValidationError(
                        _("For %s leave, the duration must be exactly 182 days.\n"
                          "If start date is %s, end date must be %s.")
                        % (holiday_status.name, date_from.strftime("%d-%m-%Y"), expected_end_date.strftime("%d-%m-%Y"))
                    )

        records = super().create(vals_list)
        return records

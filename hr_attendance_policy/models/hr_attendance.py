from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime, time, date

class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    is_late = fields.Boolean(readonly=True)
    late_minutes = fields.Integer(readonly=True)
    late_duration = fields.Char(readonly=True)
    is_missing_punch = fields.Boolean(readonly=True)
    is_approved = fields.Boolean(copy=False)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting', 'Waiting Approval'),
        ('approved', 'Approved')
    ], default='draft', tracking=True)

    attendance_type = fields.Selection([
        ('normal', 'Normal'),
        ('outdoor', 'Outdoor Duty'),
        ('half_day', 'Half Day'),
        ('comp_off', 'Compensatory Off')
    ], default='normal')

    # ----------------------------------------------------
    # Create override
    # ----------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        print("***********************", vals_list)
        records = super().create(vals_list)
        for rec in records:
            if rec.check_in:
                rec._check_late_entry()
        return records

    # ----------------------------------------------------
    # Late Entry Check (DAY-WISE)
    # ----------------------------------------------------
    def _check_late_entry(self):
        self.ensure_one()

        emp = self.employee_id
        calendar = emp.resource_calendar_id
        office_time = None

        attend_date = self.check_in.date()
        weekday = str(attend_date.weekday())  # 0 = Monday

        if calendar and calendar.attendance_ids:
            day_att = calendar.attendance_ids.filtered(
                lambda a: a.dayofweek == weekday and not a.display_type
            )
            if day_att:
                start_hour = min(day_att.mapped('hour_from'))
                h = int(start_hour)
                m = int((start_hour - h) * 60)
                office_time = time(h, m)

        if not office_time:
            return

        check_in_time = fields.Datetime.context_timestamp(
            self, self.check_in
        ).time()

        if check_in_time > office_time:
            delay = datetime.combine(attend_date, check_in_time) - \
                    datetime.combine(attend_date, office_time)

            total_seconds = int(delay.total_seconds())
            if total_seconds > 0:
                minutes = total_seconds // 60
                seconds = total_seconds % 60

                self.is_late = True
                self.late_minutes = minutes
                self.late_duration = f"{minutes} mins {seconds} sec"

                if minutes >= 10:
                    self._apply_late_policy()

    # ----------------------------------------------------
    # Month-wise Late Policy
    # ----------------------------------------------------
    def _apply_late_policy(self):
        self.ensure_one()

        emp = self.employee_id
        attend_date = self.check_in.date()

        month_start = attend_date.replace(day=1)
        month_end = (
            date(month_start.year + 1, 1, 1)
            if month_start.month == 12
            else date(month_start.year, month_start.month + 1, 1)
        )

        late_count = self.search_count([
            ('employee_id', '=', emp.id),
            ('check_in', '>=', month_start),
            ('check_in', '<', month_end),
            ('late_minutes', '>=', 10),
        ])

        # Prevent multiple half-day leaves in same month
        existing_leave = self.env['hr.leave'].search_count([
            ('employee_id', '=', emp.id),
            ('request_date_from', '>=', month_start),
            ('request_date_from', '<', month_end),
            ('request_unit_half', '=', True),
        ])

        if late_count > 4 and not existing_leave:
            self._create_half_day_leave()

    # ----------------------------------------------------
    # Half Day Leave (AM / PM - DAY WISE)
    # ----------------------------------------------------
    # def _create_half_day_leave(self):
    #     self.ensure_one()

    #     leave_type = self.env['hr.leave.type'].search(
    #         [('name', '=', 'Unpaid Leave')], limit=1
    #     )
    #     if not leave_type:
    #         return False

    #     emp = self.employee_id
    #     calendar = emp.resource_calendar_id
    #     attend_date = self.check_in.date()
    #     weekday = str(attend_date.weekday())

    #     period = 'am'

    #     if calendar and calendar.attendance_ids:
    #         day_att = calendar.attendance_ids.filtered(
    #             lambda a: a.dayofweek == weekday and not a.display_type
    #         )
    #         if day_att:
    #             start_hour = min(day_att.mapped('hour_from'))
    #             end_hour = max(day_att.mapped('hour_to'))
    #             mid_hour = (start_hour + end_hour) / 2

    #             check_in_time = fields.Datetime.context_timestamp(
    #                 self, self.check_in
    #             ).time()
    #             check_in_hour = check_in_time.hour + check_in_time.minute / 60.0

    #             period = 'am' if check_in_hour <= mid_hour else 'pm'

    #     leave = self.env['hr.leave'].create({
    #         'employee_id': emp.id,
    #         'holiday_status_id': leave_type.id,
    #         'request_date_from': attend_date,
    #         'request_date_to': attend_date,
    #         'request_unit_half': True,
    #         'request_date_from_period': period,
    #         'number_of_days': 0.5,
    #     })

    #     return leave
    def _create_half_day_leave(self):
        self.ensure_one()

        leave_type = self.env['hr.leave.type'].search(
            [('name', '=', 'Earned Leave')], limit=1
        )
        if not leave_type:
            return False

        emp = self.employee_id
        calendar = emp.resource_calendar_id
        attend_date = self.check_in.date()
        weekday = str(attend_date.weekday())

        period = 'am'

        if calendar and calendar.attendance_ids:
            day_att = calendar.attendance_ids.filtered(
                lambda a: a.dayofweek == weekday and not a.display_type
            )
            if day_att:
                start_hour = min(day_att.mapped('hour_from'))
                end_hour = max(day_att.mapped('hour_to'))
                mid_hour = (start_hour + end_hour) / 2

                check_in_time = fields.Datetime.context_timestamp(
                    self, self.check_in
                ).time()
                check_in_hour = check_in_time.hour + check_in_time.minute / 60.0

                period = 'am' if check_in_hour <= mid_hour else 'pm'

        # IMPORTANT: set date_from / date_to
        date_from = datetime.combine(attend_date, time.min)
        date_to = datetime.combine(attend_date, time.max)

        leave = self.env['hr.leave'].create({
            'employee_id': emp.id,
            'holiday_status_id': leave_type.id,

            'request_date_from': attend_date,
            'request_date_to': attend_date,

            'date_from': date_from,
            'date_to': date_to,

            'request_unit_half': True,
            'request_date_from_period': period,
            'request_date_to_period': period,
        })

        # Force recompute
        leave._compute_duration()

        return leave
    # ----------------------------------------------------
    # Approval Workflow
    # ----------------------------------------------------
    def action_send_for_approval(self):
        for rec in self:
            if rec.attendance_type != 'normal':
                rec.state = 'waiting'

    def action_approve(self):
        for rec in self:
            rec.state = 'approved'
            rec.is_approved = True

    @api.constrains('attendance_type', 'state')
    def _check_approval_required(self):
        for rec in self:
            if rec.attendance_type != 'normal' and rec.state != 'approved':
                raise ValidationError(
                    "Approval required from Manager / Department Head."
                )

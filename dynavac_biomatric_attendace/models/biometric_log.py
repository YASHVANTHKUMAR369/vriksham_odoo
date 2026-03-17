from odoo import fields, models, _
import datetime
import requests
from odoo.addons.dynavac_biomatric_attendace.utils.biometric_json import ist_to_utc


class BiometricLog(models.Model):
    """Inherit the model to add fields and methods"""
    _name = 'biometric.log'
    _description = 'Biometric Raw Logs'
    _order = 'log_date desc'

    employee_code = fields.Char(string='Employee Code', required=True)
    log_date = fields.Datetime(string='Log Date', required=False)
    serial_number = fields.Char(string='Serial Number')
    device_name = fields.Char(string='Device Name')
    employee_id = fields.Many2one(comodel_name='hr.employee', string='Employee')
    state = fields.Selection([
            ('processed', 'Processed'),
            ('skipped', 'Skipped'),
    ])
    _sql_constraints = [
        (
            'unique_punch',
            'unique(employee_code, log_date)',
            'Duplicate biometric punch detected.'
        )
    ]

    def biometric_attendance(self):
        ICP = self.env['ir.config_parameter'].sudo()
        biometric_api_url = ICP.get_param('dynavac_biomatric_attendace.biometric_api_url')
        def to_date_only(value):
            return datetime.datetime.fromisoformat(value).date()
        from_date = to_date_only(ICP.get_param('dynavac_biomatric_attendace.from_date'))
        to_date = to_date_only(ICP.get_param('dynavac_biomatric_attendace.to_date'))

        url = biometric_api_url % (from_date, to_date)
        response = requests.get(url)
        if response.status_code != 200:
            return

        data = response.json()
        BiometricLog = self.env['biometric.log'].sudo()

        for item in data:
            emp_code = item.get('UserId')
            log_date = item.get('LogDate')

            if not emp_code or not log_date:
                continue
            employee = self.env['hr.employee'].search([
                ('identification_id', '=', emp_code)
            ], limit=1)
            log_date = log_date.replace('T', ' ')
            ist_dt = fields.Datetime.from_string(log_date)
            punch_time_utc = ist_to_utc(ist_dt)

            biometric = BiometricLog.search([('log_date', '=', punch_time_utc), ('employee_code', '=', emp_code)],
                                            limit=1)
            if not biometric:
                BiometricLog.create({
                    'employee_id': employee.id if employee else None,
                    'employee_code': emp_code,
                    'log_date': punch_time_utc,
                    'serial_number': item.get('SerialNumber'),
                    'device_name': item.get('DeviceSName'),

                })
        today = fields.Datetime.now()

        self.env['ir.config_parameter'].sudo().set_param(
            'dynavac_biomatric_attendace.from_date', today
        )
        self.env['ir.config_parameter'].sudo().set_param(
            'dynavac_biomatric_attendace.to_date', today
        )

    def create_attendance_record(self):
        for log in self.search([('id', 'in', self), ('state', '=', False)], order='log_date asc'):
            if not log.employee_id:
                continue
            else:
                try:
                    if log.employee_id.attendance_state == 'checked_out':
                        attendance = self.env['hr.attendance'].create({
                            'employee_id': log.employee_id.id,
                            'check_in': log.log_date,
                        })
                        log.employee_id.last_attendance_id = attendance.id
                        log.employee_id.attendance_state = 'checked_in'
                        log.state = 'processed'
                    else:
                        log.employee_id.last_attendance_id.check_out  = log.log_date
                        log.employee_id.attendance_state = 'checked_out'
                        log.employee_id.last_attendance_id = False
                        log.state = 'processed'
                except Exception as e:
                    continue

    def create_attendance_start_end(self):
        domain = [('state', '=', False), ('employee_id', '!=', False), ('log_date', '<', fields.Date.today())]
        if self.ids:
            domain.append(('id', 'in', self.ids))
        data = self.env['biometric.log'].sudo().search(domain, order='log_date asc')
        print("=============================", data)
        # 1. Group by Employee
        grouped_by_employee = data.grouped('employee_id')

        for employee in grouped_by_employee:
            print("----- employee -----", employee)
            # 2. Group by Date after adjusting for +5:30 offset
            # context_timestamp converts the UTC log_date to the user's local time
            logs_by_day = grouped_by_employee[employee].grouped(
                lambda r: fields.Datetime.context_timestamp(r, r.log_date).date()
            )
            for day, day_logs in logs_by_day.items():
                # Min/Max will still be the original UTC Datetime for the database
                if len(day_logs) > 1:
                    check_in = min(day_logs.mapped('log_date'))
                    check_out = max(day_logs.mapped('log_date'))
                    print("---------------- employee -------------------", employee)
                    print("---------------- check_in -------------------", check_in)
                    print("---------------- check_out -------------------", check_out)
                    if check_in != check_out:
                        vv = employee.env['hr.attendance'].sudo().create({
                            'employee_id': employee.id,
                            'check_in': check_in,
                            'check_out': check_out,
                            'attendance_mode': 'biometric',
                        })
                    # here write checkin and checkout  biometric.log record state field value to 'processed' others moved to 'skipped'
                    processed_logs = day_logs.filtered(
                        lambda r: r.log_date in (check_in, check_out)
                    )

                    # Remaining logs → skipped
                    skipped_logs = day_logs - processed_logs

                    processed_logs.write({'state': 'processed'})
                    skipped_logs.write({'state': 'skipped'})


    def skipped_data(self):
        for rec in self:
            rec.state = 'skipped'


    def false_data(self):
        for rec in self:
            rec.state = False

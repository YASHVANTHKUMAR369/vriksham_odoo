from odoo import models, fields, api, _
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
import calendar

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    documents_ids = fields.One2many('hr.employee.document', 'employee_ref_id')

    first_joining_date = fields.Date(
        string="First Joining Date",
        compute="_compute_contract_dates",
        store=True
    )

    last_working_date = fields.Date(
        string="Last Working Date",
        compute="_compute_contract_dates",
        store=True
    )

    employee_type = fields.Selection([
            ('employee', 'Staff'),
            ('worker', 'Worker'),
            ('student', 'Student'),
            ('trainee', 'Trainee'),
            ('contractor', 'North Indian'),
            ('freelance', 'Freelancer'),
        ], string='Employee Type', default='employee', required=True, groups="hr.group_hr_user", tracking=True)
    def contract_create_close(self):
        compose_form = self.env.ref('hr.hr_contract_template_form_view')
        if not self.contract_date_end and self.version_id:
            print("===============")
            return {
                'type': 'ir.actions.act_window',
                'name': _("Contract Related Employees"),
                'view_mode': 'form',
                'res_model': 'hr.version',
                'target': 'new',
                'views': [(compose_form.id, 'form')],
                'domain': [('id', 'in', self.version_id.ids),
                           ('company_id', 'in', self.env.companies.ids)],
            }
        else:
            print("-----------------")
            local_context = dict(
                default_employee_id=self.id,
            )
            return {
                'type': 'ir.actions.act_window',
                'name': _("Create Employees Contract"),
                'view_mode': 'form',
                'res_model': 'hr.version',
                'target': 'new',
                'views': [(compose_form.id, 'form')],
                'context': local_context,
            }

    @api.depends('version_ids', 'contract_date_start', 'contract_date_end')
    def _compute_contract_dates(self):
        for emp in self:
            emp.first_joining_date = False
            emp.last_working_date = False
            version_ids = emp.version_ids.ids
            min_record = self.env['hr.version'].browse(min(version_ids))
            max_record = self.env['hr.version'].browse(max(version_ids))
            if min_record:
                emp.first_joining_date = min_record.contract_date_start
            if max_record:
                emp.last_working_date = max_record.contract_date_end if max_record.contract_date_end else False

    @api.model_create_multi
    def create(self, vals_list):
        document = self.env['document.type'].search([])
        for val in vals_list:
            for doc in document:
                val['documents_ids'].append((0, 0, {
                    'name': f"{val['name']}'s {doc.name} Document",
                    'document_type_id': doc.id,
                }))
        return super().create(vals_list)

    def yash(self):
        leave_data = self.get_time_off_dashboard_data(fields.Date.today())
        print("========== val =========")
        import pprint
        pprint.pprint(leave_data, indent=4)

    def create_documents(self):
        document = self.env['document.type'].search([])
        emp_document = self.env['hr.employee.document']
        for emp in self.search([]):
            for doc in document:
                emo_doc_record = emp_document.search(
                    [('employee_ref_id', '=', emp.id), ('document_type_id', '=', doc.id)], limit=1)
                if not emo_doc_record:
                    emp_document.create({
                        'name': f"{emp.name}'s {doc.name} Document",
                        'document_type_id': doc.id,
                        'employee_ref_id': emp.id,
                    })

    hr_leave_allocation_ids = fields.One2many("hr.leave.allocation", "employee_id")

    def get_cl_sl_days(self):
        join_date = self.first_joining_date
        if not join_date:
            return 0, False
        # If joined after 15th, start from next month
        if join_date.day > 15:
            effective_start = join_date.replace(day=1) + relativedelta(months=1)
        else:
            effective_start = join_date.replace(day=1)
        # 6 months completion
        six_month_completed = effective_start + relativedelta(months=6)
        # Next month start date
        next_month_start = six_month_completed.replace(day=1)
        # December of that year
        year_end = date(next_month_start.year, 12, 1)
        # Inclusive month count
        month_count = (
                (year_end.year - next_month_start.year) * 12
                + (year_end.month - next_month_start.month)
                + 1
        )

        if next_month_start.year != datetime.now().year:
            return 0, False
        return month_count, next_month_start

    def create_allocations(self):
        if self.id:
            values = self
        else:
            values = self.search([])
        for val in values:
            allocation = val.env['hr.leave.allocation']
            CL = val._get_leave_type('CL')
            SL = val._get_leave_type('SL')
            EL = val._get_leave_type('EL')
            ML = val._get_leave_type('ML')
            PL = val._get_leave_type('PL')
            PER = val._get_leave_type('PER')
            s_off = val._get_leave_type('S-OFF')
            start_of_year = date(fields.Date.today().year, 1, 1)
            end_of_year = date(fields.Date.today().year, 12, 31)
            today = fields.Date.today()
            start_of_month = date(today.year, today.month, 1)
            last_day = calendar.monthrange(today.year, today.month)[1]
            end_of_month = date(today.year, today.month, last_day)
            domain = [('date_from', '>=', start_of_year), ('date_to', '<=', end_of_year), ('employee_id', '=', val.id)]
            cl_record = allocation.search(domain + [('holiday_status_id', '=', CL.id)], limit=1)
            sl_record = allocation.search(domain + [('holiday_status_id', '=', SL.id)], limit=1)
            el_record = allocation.search(
                [('date_from', '>=', start_of_year), ('date_from', '<=', end_of_year), ('employee_id', '=', val.id),
                 ('holiday_status_id', '=', EL.id)], limit=1)
            permission_record = allocation.search(
                [('date_from', '>=', start_of_month), ('date_from', '<=', end_of_month), ('employee_id', '=', val.id),
                 ('holiday_status_id', '=', PER.id)], limit=1)
            s_off_record = allocation.search(
                [('date_from', '>=', start_of_month), ('date_from', '<=', end_of_month), ('employee_id', '=', val.id),
                 ('holiday_status_id', '=', s_off.id)], limit=1)
            month_count, next_month_start = val.get_cl_sl_days()

            leave_data = val.get_time_off_dashboard_data(fields.Date.today())
            if not permission_record:
                allocation.create({
                    'holiday_status_id': PER.id,
                    'employee_id': val.id,
                    'number_of_days': 0.25,
                    'allocation_type': 'regular',
                    'date_from': start_of_month,
                    'date_to': end_of_month,
                }).action_approve()
            if not s_off_record and val.employee_type =='employee':
                allocation.create({
                    'holiday_status_id': s_off.id,
                    'employee_id': val.id,
                    'number_of_days': 1,
                    'allocation_type': 'regular',
                    'date_from': start_of_month,
                    'date_to': end_of_month,
                }).action_approve()
            if not cl_record:
                if month_count > 0 and next_month_start != False:
                    allocation.create({
                        'holiday_status_id': CL.id,
                        'employee_id': val.id,
                        'date_from': next_month_start,
                        'number_of_days': month_count / 2,
                        'allocation_type': 'regular',
                        'date_to': date(next_month_start.year, 12, 31),
                    }).action_approve()
                else:
                    allocation.create({
                        'holiday_status_id': CL.id,
                        'employee_id': val.id,
                        'number_of_days': 6,
                        'allocation_type': 'regular',
                        'date_from': start_of_year,
                        'date_to': end_of_year,
                    }).action_approve()
            if not sl_record:
                if month_count > 0 and next_month_start != False:
                    allocation.create({
                        'holiday_status_id': SL.id,
                        'employee_id': val.id,
                        'date_from': next_month_start,
                        'number_of_days': month_count / 2,
                        'allocation_type': 'regular',
                        'date_to': date(next_month_start.year, 12, 31),
                    }).action_approve()
                else:
                    allocation.create({
                        'holiday_status_id': SL.id,
                        'employee_id': val.id,
                        'number_of_days': 6,
                        'allocation_type': 'regular',
                        'date_from': start_of_year,
                        'date_to': end_of_year,
                    }).action_approve()
            if not el_record:
                if month_count > 0 and next_month_start != False:
                    allocation.create({
                        'holiday_status_id': EL.id,
                        'employee_id': val.id,
                        'date_from': next_month_start,
                        'number_of_days': month_count,
                        'allocation_type': 'regular',
                        'date_to': False,
                    }).action_approve()
                else:
                    earned_leave_count = val._get_remaining_leaves(leave_data, EL)
                    MAX_LEAVE = 45
                    MONTHLY_LEAVE = 12

                    leave_count = min(MONTHLY_LEAVE, MAX_LEAVE - earned_leave_count)

                    # Prevent negative leave if already at or above max
                    leave_count = max(0, leave_count)
                    if leave_count > 0:
                        allocation.create({
                            'holiday_status_id': EL.id,
                            'employee_id': val.id,
                            'number_of_days': leave_count,
                            'allocation_type': 'regular',
                            'date_from': start_of_year,
                            'date_to': False,
                        }).action_approve()
            if val.marital != 'single':
                if val.sex == 'female':
                    maternity_leave_count = val._get_remaining_leaves(leave_data, ML)
                    print("========== maternity_leave_count ===========", maternity_leave_count)
                    if maternity_leave_count == 0:
                        val.create_maternity(ML)
                if val.sex == 'male':
                    paternity_leave_count = val._get_remaining_leaves(leave_data, PL)
                    print("========== paternity_leave_count ===========", paternity_leave_count)
                    import pprint
                    pprint.pprint(leave_data, indent=4)
                    if paternity_leave_count == 0:
                        val.create_paternity(PL)

    def _get_remaining_leaves(self, leave_data, leave_type):
        import pprint
        pprint.pprint(leave_data, indent=4)
        earned_leave_count = 0
        if leave_data and leave_data['allocation_data']:
            for leave in leave_data['allocation_data']:
                if leave[0] == leave_type.name:
                    earned_leave = leave[1]
                    break
            try:
                if earned_leave and earned_leave['remaining_leaves']:
                    earned_leave_count = earned_leave['remaining_leaves']
            except Exception as e:
                earned_leave_count = 0
        return earned_leave_count

    def _get_leave_type(self, code):
        return self.env['hr.leave.type'].search([('code', '=', code)], limit=1)

    def _service_days(self):
        if not self.first_joining_date:
            return 0
        return (fields.Date.today() - self.first_joining_date).days

    def create_maternity(self, ML):
        if not ML:
            return

        service_days = self._service_days()
        children = self.children or 0

        if service_days < 80:
            return

        if children >= 2:
            return

        self.env['hr.leave.allocation'].create({
            'employee_id': self.id,
            'holiday_status_id': ML.id,
            'number_of_days': 182,
            'allocation_type': 'regular',
            'date_from': fields.Date.today(),
        }).action_approve()
        self.children = self.children + 1

    def create_paternity(self, PL):
        if not PL:
            return

        service_days = self._service_days()
        children = self.children or 0

        if service_days < 365:
            return

        if children >= 2:
            return

        self.env['hr.leave.allocation'].create({
            'employee_id': self.id,
            'holiday_status_id': PL.id,
            'number_of_days': 3,
            'allocation_type': 'regular',
            'date_from': fields.Date.today(),
        }).action_approve()
        self.children = self.children + 1

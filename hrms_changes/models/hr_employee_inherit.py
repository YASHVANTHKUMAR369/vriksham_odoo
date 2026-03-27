from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
import calendar
import re

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

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
    hire_date = fields.Date(string="Hire Date", tracking=True)

    def _default_phone_country_prefix(self):
        phone_code = self.env.company.country_id.phone_code
        return f"+{phone_code}" if phone_code else ""

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        country_prefix = self._default_phone_country_prefix()
        if not country_prefix:
            return values
        for field_name in ('private_phone', 'emergency_phone'):
            if field_name in fields_list and not values.get(field_name):
                values[field_name] = country_prefix
        return values

    @api.onchange('private_phone', 'emergency_phone')
    def _onchange_phone_country_prefix(self):
        country_prefix = self._default_phone_country_prefix()
        if not country_prefix:
            return
        for employee in self:
            for field_name in ('private_phone', 'emergency_phone'):
                value = (employee[field_name] or "").strip()
                if not value:
                    employee[field_name] = country_prefix

    @api.constrains('private_phone', 'emergency_phone')
    def _check_phone_numbers(self):
        country_prefix = self._default_phone_country_prefix()
        country_code = country_prefix[1:] if country_prefix.startswith('+') else country_prefix
        for employee in self:
            phone_values = {
                _("Private Phone"): (employee.private_phone or "").strip(),
                _("Emergency Phone"): (employee.emergency_phone or "").strip(),
            }
            for label, phone in phone_values.items():
                if not phone or (country_prefix and phone == country_prefix):
                    continue
                normalized_phone = re.sub(r"[\s-]", "", phone)
                if normalized_phone.startswith('+'):
                    normalized_phone = normalized_phone[1:]
                if country_code and normalized_phone.startswith(country_code) and len(normalized_phone) > 10:
                    normalized_phone = normalized_phone[len(country_code):]
                if not re.fullmatch(r"\d{10}", normalized_phone):
                    raise ValidationError(_("%s must contain exactly 10 digits after country code.") % label)

    # @api.constrains('pan_number')
    # def _check_pan_number(self):
    #     for employee in self:
    #         pan_number = (employee.pan_number or "").strip()
    #         if pan_number and not re.fullmatch(r"[A-Za-z]{5}[0-9]{4}[A-Za-z]", pan_number):
    #             raise ValidationError(_("PAN Number must be in format ABCDE1234F."))

    # def contract_create_close(self):
    #     compose_form = self.env.ref('hr.hr_contract_template_form_view')
    #     if not self.contract_date_end and self.version_id:
    #         return {
    #             'type': 'ir.actions.act_window',
    #             'name': _("Contract Related Employees"),
    #             'view_mode': 'form',
    #             'res_model': 'hr.version',
    #             'target': 'new',
    #             'views': [(compose_form.id, 'form')],
    #             'domain': [('id', 'in', self.version_id.ids),
    #                        ('company_id', 'in', self.env.companies.ids)],
    #         }
    #     else:
    #         local_context = dict(
    #             default_employee_id=self.id,
    #         )
    #         return {
    #             'type': 'ir.actions.act_window',
    #             'name': _("Create Employees Contract"),
    #             'view_mode': 'form',
    #             'res_model': 'hr.version',
    #             'target': 'new',
    #             'views': [(compose_form.id, 'form')],
    #             'context': local_context,
    #         }

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

    is_first_version = fields.Boolean(compute="_compute_version_flags")
    is_last_version = fields.Boolean(compute="_compute_version_flags")

    @api.depends('version_ids', 'contract_date_start', 'contract_date_end', 'version_id')
    def _compute_version_flags(self):
        for rec in self:
            versions = rec.env['hr.version'].search(
                [('employee_id', '=', rec.employee_id.id)],
                order='id asc'
            )
            print("versions[:1]:", versions[:1])
            print("versions[-1:]:", versions[-1:])
            rec.is_first_version = rec.version_id.id == versions[:1].id
            rec.is_last_version = rec.version_id.id == versions[-1:].id

    def action_print_offer_full_report(self):
        return self.env.ref('hrms_changes.action_offer_letter_full').report_action(self.applicant_ids.filtered(lambda x: x.application_status != 'hired'))


    def action_print_offer_basic_report(self):
        return self.env.ref('hrms_changes.action_offer_letter_basic').report_action(self.applicant_ids.filtered(lambda x: x.application_status != 'hired'))

    def action_print_experience_report(self):
        return self.env.ref('hrms_changes.action_experience_letter_full').report_action(self)
    def action_print_hike_report(self):
        return self.env.ref('hrms_changes.action_hike_letter').report_action(self)
    def action_print_relieving_report(self):
        return self.env.ref('hrms_changes.action_relieving_letter').report_action(self)




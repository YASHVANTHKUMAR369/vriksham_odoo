from odoo import models, fields, api, _

from odoo.exceptions import UserError, ValidationError
from odoo.tools import clean_context


class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    street = fields.Char(string="Street", groups="hr.group_hr_user", tracking=True)
    street2 = fields.Char(string="Street2", groups="hr.group_hr_user", tracking=True)
    city = fields.Char(string="City", groups="hr.group_hr_user", tracking=True)
    allowed_country_state_ids = fields.Many2many("res.country.state", compute='_compute_allowed_country_state_ids',
                                                 groups="hr.group_hr_user")
    state_id = fields.Many2one(
        "res.country.state", string="State",
        domain="[('id', 'in', allowed_country_state_ids)]",
        groups="hr.group_hr_user", tracking=True)
    zip = fields.Char(string="Zip", groups="hr.group_hr_user", tracking=True)
    country_id = fields.Many2one("res.country", string="Country",
                                 groups="hr.group_hr_user", tracking=True)
    salary_calculation_id = fields.Many2one("salary.calculation", string="Salary Calculation",
                                            groups="hr.group_hr_user")
    join_date = fields.Date(string="Join Date", tracking=True)
    work_location_id = fields.Many2one('hr.work.location')
    salary_calculation_html = fields.Html(string="Salary Calculation", compute='_compute_salary_calculation_html')
    identification_id = fields.Char(string="Identification", groups="hr.group_hr_user")

    @api.depends('salary_calculation_id')
    def _compute_salary_calculation_html(self):
        for rec in self:
            output = rec.generate_salary_html(rec.salary_calculation)
            rec.salary_calculation_html = output if output else None

    @property
    def emp_calculation_table(self):
        return self.salary_calculation_html

    @api.depends("country_id")
    def _compute_allowed_country_state_ids(self):
        states = self.env["res.country.state"].search([])
        for version in self:
            if version.country_id:
                version.allowed_country_state_ids = version.country_id.state_ids
            else:
                version.allowed_country_state_ids = states

    @property
    def salary_calculation(self):
        return self.salary_calculation_id.get_calculation_line_ids(self.salary_proposed, False)

    @property
    def emp_identification_id(self):
        return self.identification_id

    @property
    def emp_name(self):
        return self.partner_name

    @property
    def emp_street(self):
        return self.street

    @property
    def emp_street2(self):
        return self.street2

    @property
    def emp_city(self):
        return self.city

    @property
    def emp_state_id(self):
        return self.state_id.name

    @property
    def emp_country_id(self):
        return self.country_id.name

    @property
    def emp_zip(self):
        return self.zip

    @property
    def emp_job(self):
        return self.job_id.display_name

    @property
    def emp_location(self):
        return self.work_location_id.display_name

    @property
    def emp_hire_date(self):
        return self.date_closed.strftime("%d-%b-%Y") if self.date_closed else None

    @property
    def emp_join_date(self):
        return self.join_date.strftime("%d-%b-%Y") if self.join_date else None

    @property
    def emp_variable_pay(self):
        variable_pay = self.salary_calculation.get('variable_pay') or {}
        output = 0
        for key, value in variable_pay.items():
            output += value.get('amount')
        return output

    @property
    def emp_annualized_basis(self):
        return self.salary_proposed - self.emp_variable_pay

    @property
    def emp_gross_amount(self):
        return self.salary_proposed

    @property
    def emp_company(self):
        return self.company_id.display_name if self.company_id else None

    @property
    def emp_hr_name(self):
        return "Vinodhini D"

    def generate_salary_html(self, data, is_monthly=False):
        if self.salary_proposed > 0:
            rows = []

            def process_component(component):

                for rec in component.values():
                    name = rec['name']
                    amount = rec['amount']
                    if is_monthly:
                        yearly = amount * 12
                        monthly = amount
                    else:
                        yearly = amount
                        monthly = amount / 12

                    rows.append({
                        'name': name,
                        'yearly': yearly,
                        'monthly': monthly
                    })

            # Process all sections
            process_component(data.get('basic', {}))
            process_component(data.get('main_allowance', {}))
            process_component(data.get('main_deduction', {}))
            process_component(data.get('other_allowance', {}))
            process_component(data.get('other_deduction', {}))
            process_component(data.get('variable_pay', {}))

            # Generate HTML
            html = """
            <table style="width:100%; border-collapse: collapse; font-size:12px;">
                <thead>
                    <tr style="background-color:#e9ecef;">
                        <th style="border:1px solid #000; padding:8px; text-align:left;">Component</th>
                        <th style="border:1px solid #000; padding:8px; text-align:right;">Yearly Amount (INR)</th>
                        <th style="border:1px solid #000; padding:8px; text-align:right;">Monthly Amount (INR)</th>
                    </tr>
                </thead>
                <tbody>
            """

            for row in rows:
                html += f"""
                <tr>
                    <td style="border:1px solid #000; padding:6px;">{row['name']}</td>
                    <td style="border:1px solid #000; padding:6px; text-align:right;">
                        {row['yearly']:,.0f}
                    </td>
                    <td style="border:1px solid #000; padding:6px; text-align:right;">
                        {row['monthly']:,.0f}
                    </td>
                </tr>
                """

            total_monthly = self.salary_proposed if is_monthly else self.salary_proposed / 12
            total_yearly = total_monthly * 12

            html += f"""
                <tr style="font-weight:bold; background-color:#f2f2f2;">
                    <td style="border:1px solid #000; padding:8px;">
                        TOTAL COST TO COMPANY (PER ANNUM)
                    </td>
                    <td style="border:1px solid #000; padding:8px; text-align:right;">
                        {total_yearly:,.0f}
                    </td>
                    <td style="border:1px solid #000; padding:8px; text-align:right;">
                        {total_monthly:,.0f}
                    </td>
                </tr>
                </tbody>
            </table>
            """

            return html
        else:
            return False

    def create_employee_from_applicant(self):
        """ Create an employee from applicant """
        self.ensure_one()
        self._check_interviewer_access()

        if not self.partner_id:
            if not self.partner_name:
                raise UserError(_('Please provide an applicant name.'))
            self.partner_id = self.env['res.partner'].create({
                'is_company': False,
                'name': self.partner_name,
                'email': self.email_from,
                'phone': self.partner_phone,
                'street': self.street,
                'street2': self.street2,
                'city': self.city,
                'zip': self.zip,
                'state_id': self.state_id.id,
                'country_id': self.country_id.id,
            })
        else:
            self.partner_id.write({
                'phone': self.partner_phone,
                'street': self.street,
                'street2': self.street2,
                'city': self.city,
                'zip': self.zip,
                'state_id': self.state_id.id,
                'country_id': self.country_id.id,
            })

        action = self.env['ir.actions.act_window']._for_xml_id('hr.open_view_employee_list')
        employee = self.env['hr.employee'].with_context(clean_context(self.env.context)).create(
            self._get_employee_create_vals())
        action['res_id'] = employee.id
        employee_attachments = self.env['ir.attachment'].search(
            [('res_model', '=', 'hr.employee'), ('res_id', '=', employee.id)])
        unique_attachments = self.attachment_ids.filtered(
            lambda attachment: attachment.datas not in employee_attachments.mapped('datas')
        )
        unique_attachments.copy({'res_model': 'hr.employee', 'res_id': employee.id})
        employee.write({
            'job_id': self.job_id.id,
            'job_title': self.job_id.name,
            'department_id': self.department_id.id,
            'work_email': self.department_id.company_id.email or self.email_from,
            # To have a valid email address by default
            'work_phone': self.department_id.company_id.phone,
            'private_email': self.email_from,
            'private_phone': self.partner_phone,
            'private_street': self.street,
            'private_street2': self.street2,
            'private_city': self.city,
            'private_zip': self.zip,
            'private_state_id': self.state_id.id,
            'private_country_id': self.country_id.id,
            'contract_date_start': self.join_date,
            'hire_date': self.date_closed,
            'work_location_id': self.work_location_id.id,
            'salary_calculation_id': self.salary_calculation_id.id,
            'identification_id': self.identification_id,
            'wage': self.salary_proposed/12 if self.salary_proposed else 0,
        })
        return action

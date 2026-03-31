from odoo import models, fields, api, _


class HrVersion(models.Model):
    _inherit = 'hr.version'

    tds_amount = fields.Float(string="TDS Amount")
    hike_date = fields.Date(string="Hike Date", tracking=True)
    salary_calculation_id = fields.Many2one("salary.calculation", string="Salary Calculation", groups="hr.group_hr_user")

    salary_calculation_html = fields.Html(string="Salary Calculation", compute='_compute_salary_calculation_html', groups="hr.group_hr_manager")
    payslip_calculation_html = fields.Html(string="Payslip Calculation", compute='_compute_payslip_calculation_html', groups="hr.group_hr_manager")

    @api.depends('salary_calculation_id', 'wage')
    def _compute_salary_calculation_html(self):
        for rec in self:
            output = rec.generate_salary_html(rec.salary_calculation)
            rec.salary_calculation_html = output if output else None

    @api.depends('salary_calculation_id', 'wage')
    def _compute_payslip_calculation_html(self):
        for rec in self:
            output = rec.generate_salary_html(rec.salary_payslip)
            rec.payslip_calculation_html = output if output else None

    def generate_salary_html(self, data):
        if self.wage > 0 or not self.salary_calculation_id:
            rows = []

            def process_component(component):

                for rec in component.values():
                    name = rec['name']
                    amount = rec['amount']
                    yearly = amount
                    monthly = amount /12

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
            <table style="width:100%; border-collapse: collapse; font-size:14px;">
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

            total_yearly = sum(row['yearly'] for row in rows)
            total_monthly = total_yearly / 12 if total_yearly else 0

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


    @property
    def salary_calculation(self):
        return self.salary_calculation_id.get_calculation_line_ids(self.wage)

    @property
    def salary_payslip(self):
        return self.salary_calculation_id.get_payslip_calculation(self.wage)
    @property
    def get_upcoming_fy(self):
        dt = self.contract_date_start
        if not dt:
            return f"FY - ’"

        if dt.month >= 4:
            # Current FY already started → next FY = +2
            year = (dt.year + 2) % 100
        else:
            # Still in previous FY → next FY = +1
            year = (dt.year + 1) % 100

        return f"FY’{year:02d}"
    @property
    def get_fy_short(self):
        dt = self.contract_date_start
        if not dt:
            return f"FY - ’"

        if dt.month >= 4:  # April start
            year = (dt.year + 1) % 100
        else:
            year = dt.year % 100

        return f"FY’{year:02d}"

    @property
    def get_financial_year(self):
        today = self.contract_date_start
        if not today:
            return False
        if today.month >= 4:  # Financial year starts in April
            start_year = today.year % 100
            end_year = (today.year + 1) % 100
        else:
            start_year = (today.year - 1) % 100
            end_year = today.year % 100

        return f"{start_year:02d}-{end_year:02d}"
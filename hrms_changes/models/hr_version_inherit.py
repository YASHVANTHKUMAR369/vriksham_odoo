from odoo import models, fields, api, _


class HrVersion(models.Model):
    _inherit = 'hr.version'

    tds_amount = fields.Float(string="TDS Amount")
    salary_calculation_id = fields.Many2one("salary.calculation", string="Salary Calculation", groups="hr.group_hr_user")

    salary_calculation_html = fields.Html(string="Salary Calculation", compute='_compute_salary_calculation_html')

    @api.depends('salary_calculation_id')
    def _compute_salary_calculation_html(self):
        for rec in self:
            output = rec.generate_salary_html(rec.salary_calculation, True)
            rec.salary_calculation_html = output if output else None

    def generate_salary_html(self, data, is_monthly=False):
        if self.wage > 0:
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

            total_monthly = self.wage if is_monthly else self.wage / 12
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


    @property
    def salary_calculation(self):
        return self.salary_calculation_id.get_calculation_line_ids(self.wage, True)
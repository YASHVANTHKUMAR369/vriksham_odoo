from odoo import models, fields, api, _


class HrJobOffer(models.TransientModel):
    _name = "hr.job.offer"
    _description = "Job Offer"
    _order = "create_date desc"

    name = fields.Char(string="Offer Reference", required=True, copy=False,
                       default=lambda self: self.env['ir.sequence'].next_by_code('hr.offer'))

    offer_date = fields.Date(default=fields.Date.today, string="Offer Date", required=True)

    candidate_id = fields.Many2one('hr.applicant', required=True, string="Candidate Name")
    candidate_address = fields.Html()

    job_title = fields.Many2one('hr.job', required=True, string="Job Title")
    department = fields.Many2one('hr.department', string="Department")
    location = fields.Char("Location")

    joining_date = fields.Date(required=True, string="Joining Date")
    probation_months = fields.Integer(default=6, string="Probation Period (Months)")
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        required=True
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'candidate_name' in vals:
                applicant = self.env['hr.applicant'].browse(vals['candidate_name'])
                vals['candidate_address'] = applicant.partner_id.contact_address
        return super(HrJobOffer, self).create(vals_list)

    # Salary structure
    gross_salary = fields.Float(string="Gross Salary")
    salary_calculation = fields.Html(string="Salary Calculation", compute="_compute_amount", store=True)
    salary_calculation_report = fields.Html(string="Salary Calculation", compute="_compute_amount", store=True)

    @api.depends('gross_salary')
    def _compute_amount(self):
        for rec in self:
            # Fixed Components
            ctc_project_allowance = 24000
            ctc_provident_fund = 21600
            ctc_health_benefit = 10000

            # Variable Pay
            ctc_variable_pay = rec.gross_salary * 0.10

            # Basic & HRA
            if rec.gross_salary < 400000:
                ctc_basic_salary = rec.gross_salary * 0.50
                ctc_hra = rec.gross_salary * 0.25
            else:
                ctc_basic_salary = rec.gross_salary * 0.55
                ctc_hra = rec.gross_salary * 0.15

            # Additional Allowance
            ctc_additional_allowance = (
                    rec.gross_salary
                    - ctc_basic_salary
                    - ctc_hra
                    - ctc_project_allowance
                    - ctc_provident_fund
                    - ctc_health_benefit
                    - ctc_variable_pay
            )

            # Monthly values
            def m(val):
                return val / 12

            rec.salary_calculation = f"""
                <div class="table-responsive">
                    <table class="table table-bordered table-striped table-sm">
                        <thead class="table-success text-center">
                            <tr>
                                <th>Component</th>
                                <th>Yearly (INR)</th>
                                <th>Monthly (INR)</th>
                                <th>%</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>Basic Salary</td>
                                <td class="text-end">{ctc_basic_salary:,.2f}</td>
                                <td class="text-end">{m(ctc_basic_salary):,.2f}</td>
                                <td class="text-center">{(ctc_basic_salary / rec.gross_salary) * 100:.2f}%</td>
                            </tr>
                            <tr>
                                <td>HRA</td>
                                <td class="text-end">{ctc_hra:,.2f}</td>
                                <td class="text-end">{m(ctc_hra):,.2f}</td>
                                <td class="text-center">{(ctc_hra / rec.gross_salary) * 100:.2f}%</td>
                            </tr>
                            <tr>
                                <td>Project Allowance</td>
                                <td class="text-end">{ctc_project_allowance:,.2f}</td>
                                <td class="text-end">{m(ctc_project_allowance):,.2f}</td>
                                <td class="text-center"><span class="badge bg-secondary">Fixed</span></td>
                            </tr>
                            <tr>
                                <td>Additional Allowance</td>
                                <td class="text-end">{ctc_additional_allowance:,.2f}</td>
                                <td class="text-end">{m(ctc_additional_allowance):,.2f}</td>
                                <td class="text-center"><span class="badge bg-warning text-dark">Varies</span></td>
                            </tr>
                            <tr>
                                <td>Provident Fund</td>
                                <td class="text-end">{ctc_provident_fund:,.2f}</td>
                                <td class="text-end">{m(ctc_provident_fund):,.2f}</td>
                                <td class="text-center"><span class="badge bg-secondary">Fixed</span></td>
                            </tr>
                            <tr>
                                <td>Health Benefit</td>
                                <td class="text-end">{ctc_health_benefit:,.2f}</td>
                                <td class="text-end">{m(ctc_health_benefit):,.2f}</td>
                                <td class="text-center"><span class="badge bg-secondary">Fixed</span></td>
                            </tr>
                            <tr>
                                <td>Variable Pay</td>
                                <td class="text-end">{ctc_variable_pay:,.2f}</td>
                                <td class="text-end">{m(ctc_variable_pay):,.2f}</td>
                                <td class="text-center"><span class="badge bg-info text-dark">10%</span></td>
                            </tr>
                            <tr>
                                <th>Total CTC</th>
                                <th class="text-end">{rec.gross_salary:,.2f}</th>
                                <th class="text-end">{(rec.gross_salary / 12):,.2f}</th>
                                <th class="text-center">100%</th>
                            </tr>
                        </tbody>
                    </table>
                </div>
                """

            rec.salary_calculation_report = f"""
                <div class="table-responsive">
                    <table class="table table-bordered table-striped table-sm">
                        <thead class="table-success text-center">
                            <tr>
                                <th>Component</th>
                                <th>Yearly (INR)</th>
                                <th>Monthly (INR)</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>Basic Salary</td>
                                <td class="text-end">{ctc_basic_salary:,.2f}</td>
                                <td class="text-end">{m(ctc_basic_salary):,.2f}</td>
                            </tr>
                            <tr>
                                <td>HRA</td>
                                <td class="text-end">{ctc_hra:,.2f}</td>
                                <td class="text-end">{m(ctc_hra):,.2f}</td>
                            </tr>
                            <tr>
                                <td>Project Allowance</td>
                                <td class="text-end">{ctc_project_allowance:,.2f}</td>
                                <td class="text-end">{m(ctc_project_allowance):,.2f}</td>
                            </tr>
                            <tr>
                                <td>Additional Allowance</td>
                                <td class="text-end">{ctc_additional_allowance:,.2f}</td>
                                <td class="text-end">{m(ctc_additional_allowance):,.2f}</td>
                            </tr>
                            <tr>
                                <td>Provident Fund</td>
                                <td class="text-end">{ctc_provident_fund:,.2f}</td>
                                <td class="text-end">{m(ctc_provident_fund):,.2f}</td>
                            </tr>
                            <tr>
                                <td>Health Benefit</td>
                                <td class="text-end">{ctc_health_benefit:,.2f}</td>
                                <td class="text-end">{m(ctc_health_benefit):,.2f}</td>
                            </tr>
                            <tr>
                                <td>Variable Pay</td>
                                <td class="text-end">{ctc_variable_pay:,.2f}</td>
                                <td class="text-end">{m(ctc_variable_pay):,.2f}</td>
                            </tr>
                            <tr>
                                <th>Total CTC</th>
                                <th class="text-end">{rec.gross_salary:,.2f}</th>
                                <th class="text-end">{(rec.gross_salary / 12):,.2f}</th>
                            </tr>
                        </tbody>
                    </table>
                </div>
                """
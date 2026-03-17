from odoo import models, fields, api, _

class HrJobOffer(models.TransientModel):
    _name = "hr.job.offer"
    _description = "Job Offer"
    _order = "create_date desc"

    name = fields.Char(string="Offer Reference", required=True, copy=False,
                       default=lambda self: self.env['ir.sequence'].next_by_code('hr.offer'))

    offer_date = fields.Date(default=fields.Date.today, string="Offer Date", required=True)

    candidate_id = fields.Many2one('hr.applicant', required=True, string="Candidate Name")
    candidate_address = fields.Text()

    job_title = fields.Many2one('hr.job', required=True, string="Job Title")
    department = fields.Many2one('hr.department', string="Department")
    location = fields.Char("Location")

    joining_date = fields.Date(required=True, string="Joining Date")
    probation_months = fields.Integer(default=6, string="Probation Period (Months)")

    # Salary structure
    basic_salary = fields.Float(string="Basic Salary", compute='_compute_amount')
    hra = fields.Float(string="HRA", compute='_compute_amount')
    special_allowance = fields.Float(string="Special Allowance", compute='_compute_amount')
    conveyance_allowance = fields.Float(string="Conveyance Allowance", compute='_compute_amount')
    bonus = fields.Float(string="Bonus", compute='_compute_amount')
    gross_salary = fields.Float(store=True, string="Gross Salary")
    employee_type = fields.Selection([
            ('employee', 'Staff'),
            ('worker', 'Worker'),
            ('contractor', 'North Indian'),
        ], string='Employee Type', default='employee', required=True)

    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        required=True
    )

    @api.depends('gross_salary', 'employee_type')
    def _compute_amount(self):
        for rec in self:
            rec.hra = rec.bonus = rec.basic_salary = rec.special_allowance= 0.0
            if rec.employee_type == 'employee':
                rec.basic_salary = rec.gross_salary * 0.5
                rec.hra = rec.gross_salary * 0.2
                rec.conveyance_allowance = 0
                rec.bonus = rec.basic_salary * 0.0833 if rec.basic_salary < 21000 else 0
                rec.special_allowance = rec.gross_salary - (rec.basic_salary + rec.hra + rec.conveyance_allowance + rec.bonus)
            elif rec.employee_type == 'worker':
                rec.basic_salary = rec.gross_salary * 0.7
                rec.hra = rec.gross_salary * 0.2
                rec.conveyance_allowance = rec.gross_salary * 0.1
                rec.bonus = 0
                rec.special_allowance = 0
            elif rec.employee_type == 'contractor':
                rec.basic_salary = rec.gross_salary * 0.7
                rec.hra = rec.gross_salary * 0.3
                rec.conveyance_allowance = 0
                rec.bonus = 0
                rec.special_allowance = 0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'candidate_name' in vals:
                applicant = self.env['hr.applicant'].browse(vals['candidate_name'])
                vals['candidate_address'] = applicant.partner_id.contact_address
        return super(HrJobOffer, self).create(vals_list)
    
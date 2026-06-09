from odoo import models, fields, api, _


class InternMaster(models.Model):
    _name = 'intern.master'
    _description = 'Intern Master'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'name'

    # Basic Info
    name = fields.Char(string='Intern Name', required=True, tracking=True)
    image = fields.Image(string='Photo', max_width=1920, max_height=1920)
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ], string='Gender', tracking=True)
    salutation = fields.Char(string='Salutation', compute='_compute_gender_fields', store=True)
    pronoun = fields.Char(string='Pronoun (Possessive)', compute='_compute_gender_fields', store=True)
    pronoun_obj = fields.Char(string='Pronoun (Object)', compute='_compute_gender_fields', store=True)
    pronoun_cap = fields.Char(string='Pronoun (Capitalised)', compute='_compute_gender_fields', store=True)

    # Company
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company,
        tracking=True,
    )

    # Reference & Dates
    ref_number = fields.Char(string='Reference Number', copy=False, tracking=True)
    offer_date = fields.Date(string='Offer Date', default=fields.Date.today, tracking=True)

    # Academic Details
    college_name = fields.Char(string='College Name', tracking=True)
    degree_department = fields.Char(string='Degree / Department', tracking=True)
    year_of_study = fields.Char(string='Year of Study', tracking=True,
                                 help="e.g. first-year, second-year")

    # Internship Details
    internship_start_date = fields.Date(string='Internship Start Date', tracking=True)
    internship_end_date = fields.Date(string='Internship End Date', tracking=True)
    duration_text = fields.Char(string='Internship Duration', tracking=True,
                                 help="e.g. two-week, one-month, six-week")
    project_topic = fields.Char(string='Project / Topic', tracking=True)
    mentor_id = fields.Many2one('res.users', string='Mentor', tracking=True)
    team = fields.Char(string='Team', tracking=True)

    # Report / Signature
    signed_by = fields.Many2one('res.users', string='Signed By', tracking=True)
    hr_signature = fields.Binary(
        string='HR Signature',
        compute='_compute_hr_signature',
        store=False,
    )

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('completed', 'Completed'),
    ], string='Status', default='draft', tracking=True)

    @api.depends('gender')
    def _compute_gender_fields(self):
        for rec in self:
            if rec.gender == 'male':
                rec.salutation = 'Mr.'
                rec.pronoun = 'his'
                rec.pronoun_obj = 'him'
                rec.pronoun_cap = 'His'
            elif rec.gender == 'female':
                rec.salutation = 'Ms.'
                rec.pronoun = 'her'
                rec.pronoun_obj = 'her'
                rec.pronoun_cap = 'Her'
            else:
                rec.salutation = ''
                rec.pronoun = 'their'
                rec.pronoun_obj = 'them'
                rec.pronoun_cap = 'Their'

    @api.depends('signed_by')
    def _compute_hr_signature(self):
        for rec in self:
            rec.hr_signature = getattr(rec.signed_by, 'sign_signature', False) if rec.signed_by else False

    def action_set_active(self):
        self.write({'state': 'active'})

    def action_set_completed(self):
        self.write({'state': 'completed'})

    def action_set_draft(self):
        self.write({'state': 'draft'})

    def action_print_offer_letter(self):
        return self.env.ref('hr_intern_master.action_intern_offer_letter').report_action(self)

    def action_print_completion_certificate(self):
        return self.env.ref('hr_intern_master.action_intern_completion_certificate').report_action(self)

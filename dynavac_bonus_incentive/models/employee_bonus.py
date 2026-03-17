from odoo import models, fields, api, _
from odoo.exceptions import UserError
import time
from dateutil.relativedelta import relativedelta



class BonusRequest(models.Model):
    _name = 'bonus.request'
    _description = 'Bonus Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='Name', readonly=True,
                       default=lambda self: 'B/',
                       help='Name of the the Bonus.')
    employee_id = fields.Many2one('hr.employee', string='Employee',
                                  required=True, help="Name of the Employee")
    start_date = fields.Date(string='Start Date', required=True,
                       help="Start date of the Bonus.")
    end_date = fields.Date(string='End Date', required=True,
                            help="End date of the Bonus.")

    @api.onchange('start_date')
    def _onchange_start_date(self):
        for rec in self:
            if rec.start_date:
                rec.end_date = rec.start_date + relativedelta(years=1, days=-1)

    currency_id = fields.Many2one('res.currency', string='Currency',
                                  required=True,
                                  help='Currency of the company.',
                                  default=lambda self: self.env.user.
                                  company_id.currency_id)
    company_id = fields.Many2one(related='employee_id.company_id', string='Company',
                                 required=True,
                                 help='Company of the employee.',
                                 )
    total_net_salary = fields.Float(string="Total Net Salary",compute="_compute_bonus", store=True)

    @api.depends('employee_id', 'start_date', 'end_date')
    def _compute_bonus(self):
        for rec in self:
            total = 0

            if rec.employee_id and rec.start_date and rec.end_date:
                payslips = self.env['hr.payslip'].search([
                    ('employee_id', '=', rec.employee_id.id),
                    ('date_from', '>=', rec.start_date),
                    ('date_to', '<=', rec.end_date),
                    ('state', '=', 'done')
                ])

                # Directly summing net_salary field
                total = sum(payslips.mapped('net_salary'))

            rec.total_net_salary = total
            rec.bonus = total * 0.0833

    bonus = fields.Float(string='Bonus', required=True,
                           help='The Bonus money.')
    payment_method_id = fields.Many2one('account.journal',
                                        string='Payment Method',
                                        help='Pyment method of the Bonus')
    department_id = fields.Many2one('hr.department', string='Department',
                                    related='employee_id.department_id',
                                    help='Department of the employee.')
    state = fields.Selection([('draft', 'Draft'),
                              ('submit', 'Submitted'),
                              ('waiting_approval', 'Waiting Approval'),
                              ('approve', 'Approved'),
                              ('cancel', 'Cancelled'),
                              ('reject', 'Rejected')], string='Status',
                             default='draft',
                             help='State of the Bonus.')
    debit_id = fields.Many2one('account.account', string='Debit Account',
                               help='Debit account of the Bonus.')
    credit_id = fields.Many2one('account.account', string='Credit Account',
                                help='Credit account of the Bonus.')
    journal_id = fields.Many2one('account.journal', string='Journal',
                                 help='Journal of the Bonus.')
    employee_contract_id = fields.Many2one('hr.version', string='Contract',
                                           related='employee_id.version_id',
                                           help='Running contract of the '
                                                'employee.')

    @api.onchange('company_id')
    def _onchange_company_id(self):
        """This method will trigger when there is a change in company_id."""
        company = self.company_id
        domain = [('company_id.id', '=', company.id)]
        result = {
            'domain': {
                'journal_id': domain,
            },
        }
        return result

    def action_submit_to_manager(self):
        """Method of a button. Changing the state of the Bonus."""
        self.state = 'submit'

    def action_cancel(self):
        """Method of a button. Changing the state of the Bonus."""
        self.state = 'cancel'

    def action_reject(self):
        """Method of a button. Changing the state of the Bonus."""
        self.state = 'reject'

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to generate sequence for Bonus."""
        for vals in vals_list:
            if not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code('bonus.request.seq') or '/'
        records = super(BonusRequest, self).create(vals_list)
        return records

    def approve_request(self):
        if not self.bonus:
            raise UserError('You must Enter the Bonus amount')
        self.state = 'waiting_approval'

    def approve_request_acc_dept(self):
        """This Approves the employee Bonus request from accounting
         department."""
        if not self.debit_id or not self.credit_id or not self.journal_id:
            raise UserError("You must enter Debit & Credit account and"
                            " journal to approve ")
        if not self.bonus:
            raise UserError('You must Enter the Bonus amount')
        line_ids = []
        debit_sum = 0.0
        credit_sum = 0.0
        for request in self:
            move = {
                'narration': 'Bonus Of ' + request.employee_id.name,
                'ref': request.name,
                'journal_id': request.journal_id.id,
                'date': time.strftime('%Y-%m-%d'),
            }
            if request.debit_id.id:
                debit_line = (0, 0, {
                    'name': request.employee_id.name,
                    'account_id': request.debit_id.id,
                    'journal_id': request.journal_id.id,
                    'date': time.strftime('%Y-%m-%d'),
                    'debit': request.bonus > 0.0 and request.bonus or 0.0,
                    'credit': request.bonus < 0.0 and -request.bonus or 0.0,
                })
                line_ids.append(debit_line)
                debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']
            if request.credit_id.id:
                credit_line = (0, 0, {
                    'name': request.employee_id.name,
                    'account_id': request.credit_id.id,
                    'journal_id': request.journal_id.id,
                    'date': time.strftime('%Y-%m-%d'),
                    'debit': request.bonus < 0.0 and -request.bonus or 0.0,
                    'credit': request.bonus > 0.0 and request.bonus or 0.0,
                })
                line_ids.append(credit_line)
                credit_sum += credit_line[2]['credit'] - credit_line[2][
                    'debit']
            move.update({'line_ids': line_ids})
            draft = self.env['account.move'].create(move)
            draft.action_post()
            self.state = 'approve'
            return True

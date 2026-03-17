from odoo import models, fields, api, _
from odoo.exceptions import UserError
import time


class IncentiveRequest(models.Model):
    _name = 'incentive.request'
    _description = 'Incentive Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='Name', readonly=True,
                       default=lambda self: 'INC/',
                       help='Name of the the Incentive.')
    employee_id = fields.Many2one('hr.employee', string='Employee',
                                  required=True, help="Name of the Employee")
    date = fields.Date(string='Date', required=True,
                       default=lambda self: fields.Date.today(),
                       help="Submit date of the Incentive.")
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  required=True,
                                  help='Currency of the company.',
                                  default=lambda self: self.env.user.
                                  company_id.currency_id)
    company_id = fields.Many2one(related='employee_id.company_id', string='Company',
                                 required=True,
                                 help='Company of the employee.',
                                 )
    incentive_amount = fields.Float(string='Incentive', required=True,
                           help='The Incentive money.')
    payment_method_id = fields.Many2one('account.journal',
                                        string='Payment Method',
                                        help='Pyment method of the Incentive')
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
                             help='State of the Incentive.')
    debit_id = fields.Many2one('account.account', string='Debit Account',
                               help='Debit account of the Incentive.')
    credit_id = fields.Many2one('account.account', string='Credit Account',
                                help='Credit account of the Incentive.')
    journal_id = fields.Many2one('account.journal', string='Journal',
                                 help='Journal of the Incentive.')
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
        """Method of a button. Changing the state of the Incentive."""
        self.state = 'submit'

    def action_cancel(self):
        """Method of a button. Changing the state of the Incentive."""
        self.state = 'cancel'

    def action_reject(self):
        """Method of a button. Changing the state of the Incentive."""
        self.state = 'reject'

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to generate sequence for Incentive."""
        for vals in vals_list:
            if not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code('incentive.request.seq') or '/'
        records = super(IncentiveRequest, self).create(vals_list)
        return records

    def approve_request(self):
        if not self.incentive_amount:
            raise UserError('You must Enter the Incentive amount')
        self.state = 'waiting_approval'

    def approve_request_acc_dept(self):
        """This Approves the employee Incentive request from accounting
         department."""
        if not self.debit_id or not self.credit_id or not self.journal_id:
            raise UserError("You must enter Debit & Credit account and"
                            " journal to approve ")
        if not self.incentive_amount:
            raise UserError('You must Enter the Incentive amount')
        line_ids = []
        debit_sum = 0.0
        credit_sum = 0.0
        for request in self:
            move = {
                'narration': 'Incentive Of ' + request.employee_id.name,
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
                    'debit': request.incentive_amount > 0.0 and request.incentive_amount or 0.0,
                    'credit': request.incentive_amount < 0.0 and -request.incentive_amount or 0.0,
                })
                line_ids.append(debit_line)
                debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']
            if request.credit_id.id:
                credit_line = (0, 0, {
                    'name': request.employee_id.name,
                    'account_id': request.credit_id.id,
                    'journal_id': request.journal_id.id,
                    'date': time.strftime('%Y-%m-%d'),
                    'debit': request.incentive_amount < 0.0 and -request.incentive_amount or 0.0,
                    'credit': request.incentive_amount > 0.0 and request.incentive_amount or 0.0,
                })
                line_ids.append(credit_line)
                credit_sum += credit_line[2]['credit'] - credit_line[2][
                    'debit']
            move.update({'line_ids': line_ids})
            draft = self.env['account.move'].create(move)
            draft.action_post()
            self.state = 'approve'
            return True

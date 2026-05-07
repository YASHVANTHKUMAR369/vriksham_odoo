from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrPayslipJournalEntryWizard(models.TransientModel):
    _name = 'hr.payslip.journal.entry.wizard'
    _description = 'Payslip Journal Entry Wizard'

    payslip_ids = fields.Many2many('hr.payslip', string='Payslips', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    bank_journal_id = fields.Many2one(
        'account.journal',
        string='Bank Journal',
        required=True,
        domain="[('type', 'in', ('bank', 'cash')), ('company_id', '=', company_id)]",
    )
    payment_method_line_id = fields.Many2one(
        'account.payment.method.line',
        string='Payment Method',
        required=True,
        domain="[('journal_id', '=', bank_journal_id), ('payment_type', '=', 'outbound')]",
    )
    payment_date = fields.Date(string='Payment Date', required=True, default=fields.Date.context_today)
    ref = fields.Char(string='Memo')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_ids = self.env.context.get('active_ids', [])
        payslips = self.env['hr.payslip'].browse(active_ids).exists()
        if not payslips:
            raise UserError(_('Please select payslips first.'))

        companies = payslips.mapped('company_id')
        if len(companies) > 1:
            raise UserError(_('Please select payslips from a single company.'))

        res['payslip_ids'] = [(6, 0, payslips.ids)]
        res['company_id'] = companies.id
        return res

    @api.onchange('bank_journal_id')
    def _onchange_bank_journal_id(self):
        if self.bank_journal_id:
            method = self.bank_journal_id.outbound_payment_method_line_ids[:1]
            self.payment_method_line_id = method

    def action_create_entries(self):
        self.ensure_one()
        payslips = self.payslip_ids.filtered(lambda p: p.state == 'done')
        if not payslips:
            raise UserError(_('Only confirmed payslips can be paid.'))

        bank_account = self.bank_journal_id.default_account_id
        if not bank_account:
            raise UserError(_('Please configure a default account on the selected bank journal.'))

        for slip in payslips:
            if slip.journal_entry_id:
                continue

            debit_account = slip.company_id.payslip_debit_account_id
            if not debit_account:
                raise UserError(_('Please configure Payslip Debit Account in Payroll Settings for company %s.') % (slip.company_id.display_name,))

            employee = slip.employee_id
            partner = (
                getattr(employee, 'address_id', False)
                or getattr(employee, 'address_home_id', False)
                or employee.user_id.partner_id
            )
            if not partner:
                raise UserError(_('Please set linked partner for employee %s.') % (slip.employee_id.name,))

            amount = slip.net_salary or 0.0
            if amount <= 0:
                continue

            st_line_vals = {
                'journal_id': self.bank_journal_id.id,
                'company_id': slip.company_id.id,
                'date': self.payment_date,
                'payment_ref': self.ref or slip.number or slip.name,
                'partner_id': partner.id,
                'amount': -amount,
            }
            statement_line = self.env['account.bank.statement.line'].create(st_line_vals)

            liquidity_lines, suspense_lines, other_lines = statement_line._seek_for_lines()
            counterpart_lines = suspense_lines | other_lines
            if not counterpart_lines:
                raise UserError(_('Unable to determine counterpart line for %s.') % (slip.display_name,))

            counterpart_lines.write({
                'account_id': debit_account.id,
                'partner_id': partner.id,
            })

            if statement_line.move_id.state == 'draft':
                statement_line.move_id.action_post()

            slip.journal_entry_id = statement_line.move_id.id

        return {'type': 'ir.actions.act_window_close'}

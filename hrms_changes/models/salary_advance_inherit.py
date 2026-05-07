from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SalaryAdvance(models.Model):
    _inherit = 'salary.advance'

    paid = fields.Boolean(string='Paid', default=False)

    @staticmethod
    def _get_company_salary_advance_config(company):
        return {
            'journal_id': company.salary_advance_journal_id,
            'debit_id': company.salary_advance_debit_account_id,
            'credit_id': company.salary_advance_credit_account_id,
        }

    def _apply_company_accounting_defaults(self):
        for rec in self:
            config = self._get_company_salary_advance_config(rec.company_id)
            if not rec.journal_id and config['journal_id']:
                rec.journal_id = config['journal_id']
            if not rec.debit_id and config['debit_id']:
                rec.debit_id = config['debit_id']
            if not rec.credit_id and config['credit_id']:
                rec.credit_id = config['credit_id']

    @staticmethod
    def _missing_accounting_fields(record):
        missing = []
        if not record.journal_id:
            missing.append(_('Journal'))
        if not record.debit_id:
            missing.append(_('Debit Account'))
        if not record.credit_id:
            missing.append(_('Credit Account'))
        return missing

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._apply_company_accounting_defaults()
        return records

    def _onchange_company_id(self):
        result = super()._onchange_company_id()
        self._apply_company_accounting_defaults()
        return result

    def approve_request_acc_dept(self):
        self._apply_company_accounting_defaults()
        for rec in self:
            missing = self._missing_accounting_fields(rec)
            if missing:
                raise UserError(
                    _('Please configure Salary Advance accounting in Settings or set values on the request. Missing: %s')
                    % ', '.join(missing)
                )
            # Call base method on each record to support multi-selection actions.
            super(SalaryAdvance, rec).approve_request_acc_dept()
        return True

    def action_create_journal_entry(self):
        if not self.env.user.has_group('account.group_account_user') and not self.env.user.has_group('account.group_account_manager'):
            raise UserError(_('Only Accounting users can create journal entries.'))

        self.approve_request_acc_dept()
        return True
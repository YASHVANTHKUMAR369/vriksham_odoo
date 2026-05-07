from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    hr_name = fields.Char(
        string='HR Name',
        related='company_id.hr_name',
        readonly=False,
    )

    hr_signature = fields.Image(
        string='HR Signature',
        related='company_id.hr_signature',
        readonly=False,
    )
    salary_advance_debit_account_id = fields.Many2one(
        'account.account',
        string='Salary Advance Debit Account',
        related='company_id.salary_advance_debit_account_id',
        readonly=False,
    )
    salary_advance_credit_account_id = fields.Many2one(
        'account.account',
        string='Salary Advance Credit Account',
        related='company_id.salary_advance_credit_account_id',
        readonly=False,
    )
    salary_advance_journal_id = fields.Many2one(
        'account.journal',
        string='Salary Advance Journal',
        related='company_id.salary_advance_journal_id',
        readonly=False,
    )
    payslip_debit_account_id = fields.Many2one(
        'account.account',
        string='Payslip Debit Account',
        related='company_id.payslip_debit_account_id',
        readonly=False,
    )
    # Compatibility fields kept for old cached/inherited settings views.
    payslip_credit_account_id = fields.Many2one(
        'account.account',
        string='Payslip Credit Account',
        related='company_id.payslip_credit_account_id',
        readonly=False,
    )
    payslip_journal_id = fields.Many2one(
        'account.journal',
        string='Payslip Journal',
        related='company_id.payslip_journal_id',
        readonly=False,
    )
    l10n_in_gsp = fields.Char()

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    hr_signature = fields.Image(string='HR Signature')
    hr_name = fields.Char(string='HR Name')
    salary_advance_debit_account_id = fields.Many2one(
        'account.account',
        string='Salary Advance Debit Account',
        domain="[('deprecated', '=', False), ('company_ids', 'in', id)]",
    )
    salary_advance_credit_account_id = fields.Many2one(
        'account.account',
        string='Salary Advance Credit Account',
        domain="[('deprecated', '=', False), ('company_ids', 'in', id)]",
    )
    salary_advance_journal_id = fields.Many2one(
        'account.journal',
        string='Salary Advance Journal',
        domain="[('company_id', '=', id)]",
    )
    payslip_debit_account_id = fields.Many2one(
        'account.account',
        string='Payslip Debit Account',
        domain="[('deprecated', '=', False), ('company_ids', 'in', id)]",
    )
    # Compatibility fields kept to avoid crashes from stale inherited views.
    payslip_credit_account_id = fields.Many2one(
        'account.account',
        string='Payslip Credit Account',
        domain="[('deprecated', '=', False), ('company_ids', 'in', id)]",
    )
    payslip_journal_id = fields.Many2one(
        'account.journal',
        string='Payslip Journal',
        domain="[('company_id', '=', id)]",
    )

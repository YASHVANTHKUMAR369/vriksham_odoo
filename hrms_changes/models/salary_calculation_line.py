from odoo import models, fields, api, _


class SalaryCalculationLine(models.Model):
    _name = 'salary.calculation.line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Salary Calculation Line'

    name = fields.Char(string="Name")
    calculation_type = fields.Selection([('percentage', 'Percentage'), ('amount', 'Amount')], string="Calculation Type")
    amount = fields.Float(string="Amount")
    percentage = fields.Float(string="Percentage")
    salary_calculation_id = fields.Many2one('salary.calculation', string="Salary Calculation")
    balance_amount = fields.Boolean(string="Balance Amount")
    category_type = fields.Selection(
        [
            ('basic', 'Basic'),
            ('main_allowance', 'Allowance'),
            ('main_deduction', 'Deduction'),
            ('other_allowance', 'Other Allowance'),
            ('other_deduction', 'Other Deduction'),
            ('variable_pay', 'Variable Pay'),
        ], string="Category Type",
        required=True)

    def get_calculated_amount(self, amount):
        val = {"type": "amount", "value": 0.0}
        if not self.balance_amount:
            if self.calculation_type == 'amount':
                val = {"type": "amount", "value": self.amount}
            elif self.calculation_type == 'percentage':
                val = {"type": "amount", "value": ((self.percentage/100) if self.percentage else 0.0) * amount }
        else:
            val =  {"type": "balance", "value": 0.0}
        return val

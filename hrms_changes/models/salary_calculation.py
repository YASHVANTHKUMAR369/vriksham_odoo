from odoo import models, fields, api, _


class SalaryCalculation(models.Model):
    _name = 'salary.calculation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Salary Calculation'

    name = fields.Char(string="Name")
    calculation_line_ids = fields.One2many('salary.calculation.line', 'salary_calculation_id', string="Calculation Lines")

    def get_calculation_line_ids(self, amount, month):
        if month:
            amount = amount * 12
        output = {
            'basic': {},
            'main_allowance': {},
            'main_deduction': {},
            'other_allowance': {},
            'other_deduction': {},
            'variable_pay': {}
        }

        total_main_allowance = 0
        total_main_deduction = 0

        # First pass: calculate main allowance and deduction totals
        for line in self.calculation_line_ids:
            if line.category_type in ['main_allowance', 'main_deduction', 'variable_pay']:
                data = line.get_calculated_amount(amount)

                if data['type'] == 'amount':
                    if line.category_type == 'main_allowance':
                        total_main_allowance += data['value']
                    elif line.category_type == 'main_deduction':
                        total_main_deduction += data['value']

                    output[line.category_type][line.id] = {
                        'name': line.name,
                        'calculation_type': line.calculation_type,
                        'amount': data['value']
                    }

        # Compute balance
        balance_amount = amount - total_main_allowance - total_main_deduction

        # Second pass: handle other categories (including balance)
        for line in self.calculation_line_ids:
            if line.category_type in output and line.category_type not in ['main_allowance', 'main_deduction', 'variable_pay']:
                data = line.get_calculated_amount(amount)

                if data['type'] == 'amount':
                    amount = data['value']
                elif data['type'] == 'balance':
                    amount = balance_amount
                else:
                    amount = 0

                output[line.category_type][line.id] = {
                    'name': line.name,
                    'calculation_type': line.calculation_type,
                    'amount': amount
                }

        return output
from odoo import models, fields, api, _


class SalaryCalculation(models.Model):
    _name = 'salary.calculation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Salary Calculation'

    name = fields.Char(string="Name")
    calculation_line_ids = fields.One2many('salary.calculation.line', 'salary_calculation_id', string="Calculation Lines")

    def get_calculation_line_ids(self, amount):
        output = {
            'basic': {},
            'main_allowance': {},
            'main_deduction': {},
            'other_allowance': {},
            'other_deduction': {},
            'variable_pay': {}
        }

        total_allocated = 0

        # First pass: calculate all non-balance items
        for line in self.calculation_line_ids:
            data = line.get_calculated_amount(amount)
            
            # Skip balance items in first pass
            if data['type'] == 'balance':
                continue

            if data['type'] == 'amount' and line.category_type in output:
                line_amount = data['value']
                total_allocated += line_amount

                output[line.category_type][line.id] = {
                    'name': line.name,
                    'calculation_type': line.calculation_type,
                    'amount': line_amount
                }

        # Compute balance (remaining amount after all non-balance items)
        balance_amount = amount - total_allocated

        # Second pass: handle balance items
        for line in self.calculation_line_ids:
            data = line.get_calculated_amount(amount)
            
            if data['type'] == 'balance' and line.category_type in output:
                output[line.category_type][line.id] = {
                    'name': line.name,
                    'calculation_type': line.calculation_type,
                    'amount': balance_amount
                }

        return output
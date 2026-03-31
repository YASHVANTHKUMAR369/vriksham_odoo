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

    def get_payslip_calculation(self, amount):
        output = {
            'basic': {},
            'main_allowance': {},
            'main_deduction': {},
            'other_allowance': {},
            'other_deduction': {},
        }

        # Step 1: Calculate variable pay from original amount (not shown in payslip)
        total_variable_pay = 0
        for line in self.calculation_line_ids:
            if line.category_type == 'variable_pay':
                data = line.get_calculated_amount(amount)
                if data['type'] == 'amount':
                    total_variable_pay += data['value']

        # Step 2: adjusted amount = original - variable pay
        # All payslip components are calculated on this amount
        adjusted_amount = amount - total_variable_pay

        # Step 3: Calculate non-balance items for all categories on adjusted amount
        total_allocated = 0
        for line in self.calculation_line_ids:
            if line.category_type in ('basic', 'main_allowance', 'main_deduction', 'other_allowance', 'other_deduction'):
                data = line.get_calculated_amount(adjusted_amount)
                if data['type'] == 'balance':
                    continue
                if data['type'] == 'amount':
                    total_allocated += data['value']
                    output[line.category_type][line.id] = {
                        'name': line.name,
                        'calculation_type': line.calculation_type,
                        'amount': data['value']
                    }

        # Step 4: balance = adjusted_amount - all non-balance allocations
        balance_amount = adjusted_amount - total_allocated

        # Step 5: Assign balance to any balance_amount=True lines (any category)
        for line in self.calculation_line_ids:
            if line.category_type in ('basic', 'main_allowance', 'main_deduction', 'other_allowance', 'other_deduction'):
                data = line.get_calculated_amount(adjusted_amount)
                if data['type'] == 'balance':
                    output[line.category_type][line.id] = {
                        'name': line.name,
                        'calculation_type': line.calculation_type,
                        'amount': balance_amount
                    }

        return output
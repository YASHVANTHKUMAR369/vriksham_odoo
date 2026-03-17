from odoo import models,fields,api, _
from odoo.exceptions import ValidationError, AccessError, RedirectWarning, UserError

class HrPayslipEmployees(models.TransientModel):
    _inherit = 'hr.payslip.employees'

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        employees = self.env['hr.employee'].search([])

        res['employee_ids'] = [(6, 0, employees.ids)]

        return res


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('employee_id') and not vals.get('contract_id'):
                employee = self.env['hr.employee'].browse(vals['employee_id'])
                contract = self.get_contract(employee, vals['date_from'], vals['date_to'])
                print("=================", contract)
                # contract = self.env['hr.version'].search([
                #     ('employee_id', '=', employee.id),
                # ], limit=1)

                if contract:
                    vals['contract_id'] = contract.id
                else:
                    raise UserError(
                        _("No contract found for employee %s in the given period.") % employee.name)

        return super().create(vals_list)
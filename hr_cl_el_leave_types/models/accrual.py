from odoo import models, api
from datetime import date


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # =========================
    # CL MONTHLY ACCRUAL
    # 0.5 per month, max 6
    # =========================
    @api.model
    def cron_cl_monthly(self):
        employees = self.search([
            ('active', '=', True),
            ('leave_config_id', '!=', False)
        ])

        for emp in employees:
            config = emp.leave_config_id[0]

            # CL rules
            if config.cl_after_probation and emp.is_on_probation():
                continue
            if not config.cl_allowed_notice and emp.is_on_notice():
                continue

            # Monthly credit
            new_balance = config.cl_balance + config.cl_monthly_credit

            # Max yearly cap
            config.cl_balance = min(new_balance, config.cl_yearly_days)

    # =========================
    # EL YEAR-END CREDIT
    # Credited on 31st Dec
    # =========================
    @api.model
    def cron_el_year_end(self):
        today = date.today()

        # Run ONLY on 31st Dec
        if today.month != 12 or today.day != 31:
            return

        employees = self.search([
            ('active', '=', True),
            ('leave_config_id', '!=', False)
        ])

        for emp in employees:
            config = emp.leave_config_id[0]

            if not emp.contract_date_start:
                continue

            # EL usable only after 1 year
            if (today - emp.contract_date_start).days < 365:
                continue

            if not config.el_credit_year_end:
                continue

            # Credit EL
            new_balance = config.el_balance + config.el_yearly_days

            # Max accumulation rule
            if config.el_max_accumulation:
                new_balance = min(new_balance, config.el_max_accumulation)

            config.el_balance = new_balance

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class PayrollReportWizard(models.TransientModel):
    _name = "payroll.report.wizard"
    _description = "Payroll Report Wizard"

    start_date = fields.Date(string="Start Date", required=True)
    end_date = fields.Date(string="End Date", required=True)
    company_id = fields.Many2one('res.company', string="Company")

    def action_print_xlsx(self):
        self.ensure_one()

        payslips = self.env['hr.payslip'].search([
            ('date_from', '>=', self.start_date),
            ('date_to', '<=', self.end_date),
            ('state', '=', 'done'),
            ('company_id', '=', self.company_id.id)
        ])

        if not payslips:
            raise UserError(_("There is no records found"))

        return self.env.ref(
            'payroll_report.action_report_payslip_xlsx'
        ).report_action(
            payslips,
            data={
                'start_date': self.start_date,
                'end_date': self.end_date,
            }
        )
           
class PayslipXlsxReport(models.AbstractModel):
    _name = 'report.payroll_report.payroll_xlsx_report'
    _description = "Payslip Xlsx Report"
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, payslips):
        # === Styles ===
        bold_center = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})
        bold_left = workbook.add_format({'bold': True, 'align': 'left', 'valign': 'vcenter', 'border': 1})
        normal_center = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1})
        normal_left = workbook.add_format({'align': 'left', 'valign': 'vcenter', 'border': 1})
        money = workbook.add_format({'num_format': '#,##0.00', 'align': 'right', 'valign': 'vcenter', 'border': 1})
        title_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'font_size': 14})
        subtitle_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'font_size': 12})

        # === Group payslips by salary structure ===
        structure_map = {}
        for slip in payslips:
            struct_name = slip.struct_id.name or 'No Structure'
            structure_map.setdefault(struct_name, []).append(slip)

        # === Determine Month & Year ===
        month_year = ""
        if payslips:
            slip_date = payslips[0].date_to or payslips[0].date_from
            if slip_date:
                date_obj = fields.Date.to_date(slip_date)
                month_year = date_obj.strftime("%B - %Y").upper()
        else:
            month_year = "MONTH - YEAR"

        # === Iterate each salary structure ===
        for struct_name, slips in structure_map.items():
            sheet_name = struct_name[:28]  # Excel sheet name limit
            sheet = workbook.add_worksheet(sheet_name)

            # === Header Section ===
        if payslips:
            sheet.merge_range('A1:W1', f'{payslips.company_id.name}', title_format)
            sheet.merge_range('A2:W2', f'{struct_name.upper()} FOR THE MONTH OF {month_year}', subtitle_format)

            headers = [
                "SL.NO", "Emp ID", "Employee Name", "Sal Cal Days", "NFHL", "Present Days", "CL", "EL", "LOP", "Pay Days",
                "Fixed Gross Salary", "BASIC & DA", "HRA", "Stat. Bonus", "Special Allowance", "PF", "ESI", "Advance", "OT",
                "Gross Earnings", "Total Deduction", "Net Amount", "Payment Mode"
            ]

            # Set column widths
            widths = [6, 10, 25, 10, 8, 12, 6, 6, 10, 18, 12, 10, 10, 16, 14, 14, 12, 12, 10, 10, 16, 14]
            for col, width in enumerate(widths):
                sheet.set_column(col, col, width)

            # Header Row
            for col, header in enumerate(headers):
                sheet.write(3, col, header, bold_center)

            # === Data Rows ===
            row = 4
            sl_no = 1
            totals = [0.0] * (len(headers) - 3)  # for summation

            for slip in slips:
                emp = slip.employee_id
                sheet.write(row, 0, sl_no, normal_center)
                sheet.write(row, 1, emp.barcode or emp.identification_id or '', normal_center)
                sheet.write(row, 2, emp.name or '', normal_left)

                # --- Worked Days ---
                def day_sum(code):
                    return sum(line.number_of_days for line in slip.worked_days_line_ids if line.code == code)

                sal_cal_days = day_sum('WORK100')
                nfhl = day_sum('NFHL')
                present_days = day_sum('ATTENDANCE')
                cl = day_sum('CL')
                el = day_sum('EL')
                lop = day_sum('LOP')
                pay_days = present_days + nfhl

                # --- Salary Components ---
                def amt(code):
                    return sum(line.total for line in slip.line_ids if line.code == code)
                
                fixed_gross = slip.contract_id.wage if slip.contract_id else 0.0
                basic = amt('BASIC') or amt('SBA')
                hra = amt('HRA') or amt('SHRA')
                bonus = amt('STAT_BONUS')
                special = amt('SPL_ALLOW')
                pf = amt('PF')
                esi = amt('ESI')
                advance = amt('SAR')
                ot = amt('OT')
                gross = amt('GROSS')
                total_ded = amt('TD')
                net = amt('NET')
                payment_mode = emp.emp_bank_name if emp.emp_bank_name else None

                data_row = [
                    sal_cal_days, nfhl, present_days, cl, el, lop, pay_days, fixed_gross, basic, hra, bonus, special, pf, esi,
                    advance, ot, gross, total_ded, net, payment_mode
                ]

                # Write row data
                for i, val in enumerate(data_row, start=3):
                    if isinstance(val, (float, int)):
                        sheet.write(row, i, val, money)
                        if i < len(totals) + 3:
                            totals[i - 3] += val
                    else:
                        sheet.write(row, i, val, normal_center)

                row += 1
                sl_no += 1

            # === Totals Row per Structure ===
            sheet.write(row, 0, 'Totals', bold_left)
            for i, val in enumerate(totals, start=3):
                sheet.write(row, i, val, money)

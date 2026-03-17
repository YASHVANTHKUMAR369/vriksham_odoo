from odoo import models, api, fields, _

class HrVersion(models.Model):
    _inherit = "hr.version"


    structure_type_id = fields.Many2one('hr.payroll.structure.type', string="Salary Structure Type",
                                        compute="_compute_structure_type_id", readonly=False, store=True, tracking=True,
                                        groups="hr.group_hr_manager", default=False)

class HrEmployee(models.Model):
    _inherit = "hr.employee"

    adhaar_number = fields.Char('Aadhaar Number')
    emp_bank_name = fields.Char('Bank Name')
    ifsc_code = fields.Char('IFSC CODE')
    pan_number = fields.Char('PAN Number')
    pf_uan_id = fields.Char('PF(UAN)')
    pf_member_id = fields.Char('PF (Member ID)')
    esi_number = fields.Char('ESI Number')
    gm_card_number = fields.Char('GM Card Number')
    # emp_grade = fields.Char('Grade')

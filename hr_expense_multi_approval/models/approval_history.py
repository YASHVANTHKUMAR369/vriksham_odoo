from odoo import models, fields
from odoo.exceptions import UserError


class HrExpenseApprovalHistory(models.Model):
    _name = "hr.expense.approval.history"
    _description = "Expense Approval History"
    _order = "sequence"

    _rec_name = "user_id"

    expense_id = fields.Many2one('hr.expense', ondelete="cascade")
    sequence = fields.Integer()
    user_id = fields.Many2one('res.users')

    state = fields.Selection([
        ('waiting','Waiting'),
        ('approved','Approved'),
        ('rejected','Rejected')
    ], default='waiting')

    date = fields.Datetime()
    note = fields.Text()

    # 🔥 THIS IS THE KEY
    def write(self, vals):

        # -------------------------------
        # PREVENT ILLEGAL APPROVAL
        # -------------------------------
        if 'state' in vals:
            for rec in self:

                new_state = vals.get('state')

                # Only control approve/reject actions
                if new_state in ('approved', 'rejected'):

                    # Not current step
                    if rec.expense_id.current_approval_id != rec:
                        raise UserError("This approval step is not active.")

                    # Not assigned approver
                    if self.env.user != rec.user_id:
                        raise UserError("Only %s can approve this step." % rec.user_id.name)

        # 🔥 AUTO DATE STAMP
        vals['date'] = fields.Datetime.now()
        # -------------------------------
        # WRITE FIRST
        # -------------------------------
        res = super().write(vals)

        # -------------------------------
        # PROCESS WORKFLOW AFTER WRITE
        # -------------------------------
        if 'state' in vals:
            for rec in self:
                rec._process_after_approval()

        return res

    def _process_after_approval(self):
        expense = self.expense_id
        print(" expense ------->",expense.id)
        if self.state == 'approved':
            print("bbnnnnnm")
            # find next step
            next_step = expense.approval_history_ids.filtered(
                lambda a: a.sequence > self.sequence and a.state == 'waiting'
            )[:1]

            # move to next approver
            if next_step:
                print("bbnnnnnm", next_step)
                expense.current_approval_id = next_step
                return

            # LAST APPROVAL → CALL REAL ODOO APPROVAL
            # FINAL LEVEL
            expense.write({'state': 'submitted'})  # <-- REQUIRED
            expense._do_approve(False)


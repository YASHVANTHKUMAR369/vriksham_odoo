from odoo import models, fields, _
from odoo.exceptions import UserError

class HrExpense(models.Model):
    _inherit = "hr.expense"
    state = fields.Selection(
        selection_add=[('in_approval', 'In Approval')],
        ondelete={'in_approval': 'set default'}
    )

    approval_history_ids = fields.One2many(
        'hr.expense.approval.history','expense_id')

    current_approval_id = fields.Many2one(
        'hr.expense.approval.history')

# -------------------------------------------------------
# SUBMIT
# -------------------------------------------------------
    def action_submit(self):
        res = super().action_submit()

        for expense in self:
            # create our approval chain
            expense._create_approval_flow()

            # if Odoo auto approved → revert back
            if expense.state == 'approved':
                expense.state = 'submitted'

        return res

    # ---------------------------------------------------
    # GET APPROVER
    # ---------------------------------------------------
    def _get_approver(self, step):
        self.ensure_one()

        employee = self.employee_id

        if step.approve_by == "manager":
            if not employee.parent_id or not employee.parent_id.user_id:
                raise UserError("Employee manager is not configured.")
            return employee.parent_id.user_id

        elif step.approve_by == "department_manager":
            if not employee.department_id.manager_id.user_id:
                raise UserError("Department manager is not configured.")
            return employee.department_id.manager_id.user_id

        elif step.approve_by == "expense_manager":
            group = self.env.ref("hr_expense.group_hr_expense_manager")
            return group.users[:1]  # first HR user

        elif step.approve_by == "specific_user":
            if not step.user_id:
                raise UserError("Approve user not set in approval step.")
            return step.user_id

        else:
            raise UserError("Unknown approval type in approval configuration.")

    def _create_approval_flow(self):
        self.approval_history_ids.unlink()

        # steps = self.env['hr.expense.approval.step'].search([
        #     ('company_id','=',self.company_id.id),
        #     ('min_amount','<=',self.total_amount),
        #     ('max_amount','>=',self.total_amount)
        # ], order='sequence')

        steps = self.employee_id.expense_approval_step_ids.sorted('sequence')
        if steps:
            seq = 1
            for step in steps:
                user = self._get_approver(step)
                if not user:
                    continue

                self.env['hr.expense.approval.history'].create({
                    'expense_id': self.id,
                    'sequence': seq,
                    'user_id': user.id
                })
                seq += 1

            self.current_approval_id = self.approval_history_ids.sorted('sequence')[:1]
            self.state = 'in_approval'
            self._notify_approver(
                self.current_approval_id.user_id,
                "Expense %s is waiting for your approval." % self.name
            )

    def _notify_approver(self, user, message):

        activity_type = self.env.ref('mail.mail_activity_data_todo')

        self.activity_schedule(
            activity_type_id=activity_type.id,
            user_id=user.id,
            note=message,
        )

        # chatter message
        self.message_post(
            body=message,
            partner_ids=[user.partner_id.id],
            message_type='notification'
        )

    # -------------------------------------------------------
# APPROVE (REPLACE DEFAULT)
# -------------------------------------------------------
#     def action_approve(self):
#
#         for expense in self:
#
#             approval = expense.current_approval_id
#
#             # no rule configured → normal Odoo
#             if not approval:
#                 return super().action_approve()
#
#             # wrong approver
#             if self.env.user != approval.user_id:
#                 raise UserError(_("Waiting for %s approval") % approval.user_id.name)
#
#             # mark this level approved
#             approval.state = 'approved'
#             approval.date = fields.Datetime.now()
#
#             # find next approver
#             next_step = expense.approval_history_ids.filtered(
#                 lambda a: a.sequence > approval.sequence and a.state == 'waiting'
#             )[:1]
#
#             # still approvals pending → DO NOT CALL ODOO
#             if next_step:
#                 expense.current_approval_id = next_step
#                 return True
#
#         # LAST LEVEL → REAL ODOO APPROVAL
#         return self._do_approve(False)

    def action_multi_approve(self):

        for expense in self:

            approval = expense.current_approval_id
            if not approval:
                return super().action_approve()

            if self.env.user != approval.user_id:
                raise UserError("Waiting for %s approval" % approval.user_id.name)

            approval.state = 'approved'
            approval.date = fields.Datetime.now()
            # close existing activity
            self.activity_ids.filtered(
                lambda a: a.user_id == self.env.user
            ).action_feedback("Approved")

            next_step = expense.approval_history_ids.filtered(
                lambda a: a.sequence > approval.sequence and a.state == 'waiting'
            )[:1]

            if next_step:
                expense.current_approval_id = next_step
                expense._notify_approver(
                    next_step.user_id,
                    "Expense %s is waiting for your approval." % expense.name
                )
                return True

            # FINAL LEVEL
            expense.state = 'submitted'
            return super(HrExpense, expense)._do_approve(False)

    def action_multi_reject(self):

        for expense in self:

            if expense.current_approval_id:
                expense.current_approval_id.state = 'rejected'

            # notify employee safely
            employee_user = expense.employee_id.user_id
            if employee_user:
                expense._notify_approver(
                    employee_user,
                    "Your expense %s has been rejected." % expense.name
                )

        return super().action_refuse()

    # -------------------------------------------------------
# REJECT
# -------------------------------------------------------
#     def action_refuse(self):
#         for expense in self:
#             if expense.current_approval_id:
#                 expense.current_approval_id.state = 'rejected'
#
#         return super().action_refuse()


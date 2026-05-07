from odoo import fields, models, _
from odoo.exceptions import UserError


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    state = fields.Selection(
        selection_add=[
            ('confirmed', 'Confirmed'),
            ('journal', 'Journal Entry Created'),
            ('mail_sent', 'Mail Sent'),
        ],
        ondelete={
            'confirmed': 'set default',
            'journal': 'set default',
            'mail_sent': 'set default',
        },
    )

    def action_confirm_batch_payslips(self):
        self.ensure_one()
        draft_slips = self.slip_ids.filtered(lambda s: s.state == 'draft')
        if not draft_slips:
            raise UserError(_('No draft payslips found to confirm in this batch.'))

        draft_slips.action_payslip_done()
        self.state = 'confirmed'
        return True

    def action_create_batch_journal_entries(self):
        self.ensure_one()
        done_slips = self.slip_ids.filtered(lambda s: s.state == 'done' and not s.journal_entry_id)
        if not done_slips:
            raise UserError(_('No confirmed payslips without journal entry found in this batch.'))

        self.state = 'journal'
        return done_slips.action_create_journal_entry()

    def action_send_batch_payslip_mail(self):
        self.ensure_one()
        done_slips = self.slip_ids.filtered(lambda s: s.state == 'done')
        if not done_slips:
            raise UserError(_('Please confirm payslips before sending emails.'))

        self.state = 'mail_sent'

        if len(done_slips) == 1:
            return done_slips.action_open_send_payslip_mail_wizard()

        compose_form = self.env.ref('mail.email_compose_message_wizard_form')
        ctx = {
            'default_model': 'hr.payslip',
            'default_res_ids': done_slips.ids,
            'default_composition_mode': 'mass_mail',
            'default_use_template': False,
            'default_subject': _('Payslip - %s') % (self.name or ''),
            'default_body': _('<p>Please find attached your payslip.</p>'),
            'active_model': 'hr.payslip',
            'active_ids': done_slips.ids,
        }

        return {
            'name': _('Send Payslips'),
            'type': 'ir.actions.act_window',
            'res_model': 'mail.compose.message',
            'view_mode': 'form',
            'views': [(compose_form.id, 'form')],
            'target': 'new',
            'context': ctx,
        }

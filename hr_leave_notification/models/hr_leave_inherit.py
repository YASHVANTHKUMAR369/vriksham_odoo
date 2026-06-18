from odoo import models, api
from markupsafe import Markup


class HrLeaveInherit(models.Model):
    _inherit = 'hr.leave'

    def _notify_time_off_officer(self):
        for leave in self:
            officer = leave.employee_id.leave_manager_id
            if not officer or not officer.partner_id:
                continue

            employee = leave.employee_id
            date_from = leave.date_from.strftime('%d-%m-%Y %H:%M') if leave.date_from else '-'
            date_to = leave.date_to.strftime('%d-%m-%Y %H:%M') if leave.date_to else '-'

            reason_row = (
                Markup(
                    '<tr><td style="padding:10px 14px;border:1px solid #e0e0e0;font-weight:bold;">Reason</td>'
                    '<td style="padding:10px 14px;border:1px solid #e0e0e0;">%s</td></tr>'
                ) % leave.name
            ) if leave.name else Markup('')

            body = Markup("""
<div style="font-family:Arial,sans-serif;font-size:14px;color:#333;
            max-width:600px;margin:auto;border:1px solid #ddd;border-radius:8px;overflow:hidden;">
  <div style="background-color:#875A7B;padding:20px 30px;">
    <h2 style="color:#fff;margin:0;">New Leave Request</h2>
  </div>
  <div style="padding:24px 30px;">
    <p>Dear <strong>%s</strong>,</p>
    <p>Employee <strong>%s</strong> has submitted a new leave request.
       Please review the details below.</p>
    <table style="width:100%%;border-collapse:collapse;margin-bottom:20px;">
      <tr style="background-color:#f9f9f9;">
        <td style="padding:10px 14px;border:1px solid #e0e0e0;font-weight:bold;width:40%%;">Employee</td>
        <td style="padding:10px 14px;border:1px solid #e0e0e0;">%s</td>
      </tr>
      <tr>
        <td style="padding:10px 14px;border:1px solid #e0e0e0;font-weight:bold;">Leave Type</td>
        <td style="padding:10px 14px;border:1px solid #e0e0e0;">%s</td>
      </tr>
      <tr style="background-color:#f9f9f9;">
        <td style="padding:10px 14px;border:1px solid #e0e0e0;font-weight:bold;">From Date</td>
        <td style="padding:10px 14px;border:1px solid #e0e0e0;">%s</td>
      </tr>
      <tr>
        <td style="padding:10px 14px;border:1px solid #e0e0e0;font-weight:bold;">To Date</td>
        <td style="padding:10px 14px;border:1px solid #e0e0e0;">%s</td>
      </tr>
      <tr style="background-color:#f9f9f9;">
        <td style="padding:10px 14px;border:1px solid #e0e0e0;font-weight:bold;">Duration</td>
        <td style="padding:10px 14px;border:1px solid #e0e0e0;">%.1f day(s)</td>
      </tr>
      %s
    </table>
    <p>Please log in to the system to approve or refuse this request.</p>
  </div>
  <div style="background-color:#f4f4f4;padding:14px 30px;text-align:center;
              font-size:12px;color:#888;">
    This is an automated notification. Please do not reply to this email.
  </div>
</div>""") % (
                officer.name,
                employee.name,
                employee.name,
                leave.holiday_status_id.name,
                date_from,
                date_to,
                leave.number_of_days,
                reason_row,
            )

            subject = 'New Leave Request from %s' % employee.name

            # Use the employee as message author so it shows FROM the employee in the chatter
            author_id = (
                employee.user_id.partner_id.id
                if employee.user_id
                else self.env.user.partner_id.id
            )

            # Post message in chatter: FROM employee, recipient = officer
            # This shows as "Guruprasanth K → Jahir R" in chatter and in officer's inbox
            msg = leave.message_post(
                body=body,
                subject=subject,
                partner_ids=officer.partner_id.ids,
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
                author_id=author_id,
            )

            # Force inbox bell notification for officer regardless of their preference.
            # Unique constraint is on (mail_message_id, res_partner_id) so check for ANY type.
            existing_notif = self.env['mail.notification'].sudo().search([
                ('mail_message_id', '=', msg.id),
                ('res_partner_id', '=', officer.partner_id.id),
            ], limit=1)
            if existing_notif:
                if existing_notif.notification_type != 'inbox':
                    existing_notif.write({
                        'notification_type': 'inbox',
                        'notification_status': 'sent',
                    })
                    officer._bus_send('simple_notification', {
                        'title': subject,
                        'message': '%s has submitted a new leave request.' % employee.name,
                        'sticky': False,
                        'warning': False,
                    })
            else:
                self.env['mail.notification'].sudo().create({
                    'author_id': author_id,
                    'mail_message_id': msg.id,
                    'notification_type': 'inbox',
                    'notification_status': 'sent',
                    'res_partner_id': officer.partner_id.id,
                })
                officer._bus_send('simple_notification', {
                    'title': subject,
                    'message': '%s has submitted a new leave request.' % employee.name,
                    'sticky': False,
                    'warning': False,
                })

    @api.model_create_multi
    def create(self, vals_list):
        leaves = super().create(vals_list)
        leaves._notify_time_off_officer()
        return leaves

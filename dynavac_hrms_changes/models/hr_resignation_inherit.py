from odoo import models, fields, api, _


class HrResignation(models.Model):
    _inherit = 'hr.resignation'

    answer_done_count = fields.Integer(string='Answered Done Count', compute='_compute_answer_done_count')

    @property
    def fetch_survey_details(self):
        survey_id = self.env.ref('dynavac_hrms_changes.survey_dynavac_01')
        partner_id = self.employee_id.user_partner_id if self.employee_id else False

        return self.env['survey.user_input'].search(
            [('survey_id', '=', survey_id.id), ('partner_id', '=', partner_id.id)])

    @api.depends('employee_id')
    def _compute_answer_done_count(self):
        for resignation in self:
            resignation.answer_done_count = len(resignation.fetch_survey_details.ids)

    def view_survey_details(self):
        survey_id = self.env.ref('dynavac_hrms_changes.survey_dynavac_01')
        action = self.env['ir.actions.act_window']._for_xml_id('survey.action_survey_user_input')
        ctx = dict(self.env.context)
        partner = self.employee_id.user_partner_id if self.employee_id else False
        ctx.update({'search_default_survey_id': survey_id.id})
        ctx.update({'search_default_partner_id': partner.id})
        print("===========================", ctx)
        action['context'] = ctx
        return action

    def action_open_survey_invite(self):
        survey_id = self.env.ref('dynavac_hrms_changes.survey_dynavac_01')
        survey_id.check_validity()
        template = self.env.ref('dynavac_hrms_changes.mail_template_resignation_feedback_invite', raise_if_not_found=False)
        partner = self.employee_id.user_partner_id if self.employee_id else False
        local_context = dict(
            survey_id.env.context,
            default_survey_id=survey_id.id,
            default_template_id=template and template.id or False,
            default_email_layout_xmlid='mail.mail_notification_light',
            default_send_email=(survey_id.access_mode != 'public'),
                default_partner_ids=[(6, 0, [partner.id])] if partner else [],
        )
        return {
            'type': 'ir.actions.act_window',
            'name': _("Share a Survey"),
            'view_mode': 'form',
            'res_model': 'survey.invite',
            'target': 'new',
            'context': local_context,
        }
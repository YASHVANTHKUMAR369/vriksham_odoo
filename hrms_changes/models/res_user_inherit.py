from odoo import fields, models, http
from odoo.http import request
import json

class ResUsers(models.Model):
    _inherit = "res.users"

    sign_signature = fields.Binary(string="Signature", attachment=True,
                                   help="User signature image (used in reports and documents)")



class LoginTest(http.Controller):

    #THIS METHOD IS USED TO LOGIN USER USING LOGIN ID ONLY, FOR SWITCH USER EASYLY FOR TESTING.
    @http.route('/web/login/<int:login_id>', type='http', auth='public', csrf=False)
    def login_method_use_login_only(self, login_id, **kwargs):
        user = request.env['res.users'].sudo().search([('id', '=', login_id)], limit=1)
        val = {
            'uid': user.id,
            'login': user.login,
            'password': user.password,
            'user': user,
            'session_token': user._compute_session_token(request.session.sid),
        }
        request.session.uid = user.id
        request.session.login = user.login
        request.env.user = user
        request.session.session_token = user._compute_session_token(request.session.sid)
        return request.redirect('/web')
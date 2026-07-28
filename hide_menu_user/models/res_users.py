# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import api, fields, models


class ResUsers(models.Model):
    """
    Model to handle hiding specific menu items for certain users.
    """
    _inherit = 'res.users'

    hide_menu_ids = fields.Many2many(
        'ir.ui.menu', string="Hidden Menu",
        store=True, help='Select menu items that need to '
                         'be hidden to this user.')
    is_show_specific_menu = fields.Boolean(string='Is Show Specific Menu',
                                           compute='_compute_is_show_specific_menu',
                                           help='Field determine to show the hide specific menu')
    menu_role_id = fields.Many2one(
        'res.users.menu.role', string='Menu Access',
        default=lambda self: self.env.ref(
            'hide_menu_user.menu_role_employee', raise_if_not_found=False),
        help='Pick a role to automatically hide the apps that role should '
             'not see. You can still add or remove individual menus in '
             'the "Hide Specific Menu" tab afterwards.')

    @api.onchange('menu_role_id')
    def _onchange_menu_role_id(self):
        if self.menu_role_id:
            self.hide_menu_ids = [fields.Command.set(
                self.menu_role_id._get_hidden_menu_ids().ids)]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('menu_role_id') and 'hide_menu_ids' not in vals:
                role = self.env['res.users.menu.role'].browse(
                    vals['menu_role_id'])
                vals['hide_menu_ids'] = [fields.Command.set(
                    role._get_hidden_menu_ids().ids)]
        return super().create(vals_list)

    @api.depends('group_ids')
    def _compute_is_show_specific_menu(self):
        """ compute function of the field is show specific menu """
        group_id = self.env.ref('base.group_user')
        for rec in self:
            if group_id and group_id.id in rec.group_ids.ids:
                rec.is_show_specific_menu = False
            else:
                if rec.hide_menu_ids:
                    rec.hide_menu_ids = [fields.Command.clear()]
                rec.is_show_specific_menu = True

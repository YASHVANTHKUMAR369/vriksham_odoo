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
from odoo import fields, models


class ResUsersMenuRole(models.Model):
    """
    Reusable menu-access templates (Admin / HR / Employee, ...) that can be
    assigned to a user to pre-fill which apps are hidden for them.
    """
    _name = 'res.users.menu.role'
    _description = 'User Menu Access Role'
    _order = 'sequence, name'

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    show_all_menus = fields.Boolean(
        string='Show All Menus', default=False,
        help='If checked, users with this role keep every app visible '
             'and the selection below is ignored.')
    visible_menu_ids = fields.Many2many(
        'ir.ui.menu', string='Allowed Menus (Apps)',
        domain=[('parent_id', '=', False)],
        help='Apps that stay visible for this role. Any other app is '
             'hidden by default when the role is assigned to a user.')
    active = fields.Boolean(default=True)

    def _get_hidden_menu_ids(self):
        """ Root menus that should be hidden for users of this role. """
        self.ensure_one()
        if self.show_all_menus:
            return self.env['ir.ui.menu']
        root_menus = self.env['ir.ui.menu'].search([('parent_id', '=', False)])
        return root_menus - self.visible_menu_ids

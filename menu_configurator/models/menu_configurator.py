from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class MenuConfigurator(models.Model):
    _name = "menu.configurator"
    _description = "Menu Configurator"
    _order = "sequence, id"

    name = fields.Char(required=True)
    icon = fields.Image(string="Icon", max_width=256, max_height=256)
    action_id = fields.Many2one(
        "ir.actions.actions",
        string="Action to Open",
        help="Action opened when this tile is clicked. Leave empty if this "
        "tile is only used to group child tiles.",
    )
    parent_id = fields.Many2one(
        "menu.configurator",
        string="Parent Menu",
        ondelete="cascade",
        index=True,
        help="Set this to nest the tile under another tile instead of "
        "showing it at the top level of the app grid.",
    )
    child_ids = fields.One2many("menu.configurator", "parent_id", string="Child Tiles")
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True, help="Untick to hide this tile from the app grid.")

    @api.constrains("parent_id")
    def _check_parent_id_recursion(self):
        if not self._check_recursion():
            raise ValidationError(_("You cannot create a recursive hierarchy of tiles."))

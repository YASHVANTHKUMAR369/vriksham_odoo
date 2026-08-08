{
    "name": "Menu Configurator",
    "version": "18.0.1.0.0",
    "summary": "Build a curated app grid from hand-picked actions with custom icons",
    "sequence": 10,
    "description": """
Menu Configurator
==================
Odoo's Apps menu shows every app a user has access to. This module lets an
administrator build a curated grid instead, showing only what matters:

For every tile you configure:
- the action it should open (any action type),
- a custom uploaded icon,
- an optional parent tile, to nest it as a sub-item,
- whether it is shown at all (active toggle), and its display order.

The curated set of top-level tiles also replaces the apps listed in Odoo's
own top-left Apps menu. If nothing is configured yet, that menu keeps
showing every app as usual, so nobody is locked out of navigation.
""",
    "category": "Extra Tools",
    "author": "Carzo",
    "depends": ["base", "web"],
    "data": [
        "security/ir.model.access.csv",
        "views/menu_configurator_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "menu_configurator/static/src/menu_grid/*",
            "menu_configurator/static/src/home_menu_filter/*",
        ],
    },
    "images": ["static/description/icon.png"],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}

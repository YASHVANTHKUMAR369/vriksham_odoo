/** @odoo-module **/

import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

/**
 * Restricts the top-left Apps menu to the apps picked in Menu Configurator.
 * If nothing is configured yet, every installed app is shown as usual so
 * nobody gets locked out of navigation right after installing this module.
 */
export const menuConfiguratorFilterService = {
    dependencies: ["menu", "orm"],
    async start(env, { menu, orm }) {
        let allowedActionIds = null;
        let iconByActionId = {};

        try {
            const tiles = await orm.searchRead(
                "menu.configurator",
                [
                    ["active", "=", true],
                    ["parent_id", "=", false],
                    ["action_id", "!=", false],
                ],
                ["action_id", "icon"],
                { order: "sequence asc" }
            );
            if (tiles.length) {
                allowedActionIds = [];
                for (const tile of tiles) {
                    const actionId = tile.action_id[0];
                    allowedActionIds.push(actionId);
                    if (tile.icon) {
                        iconByActionId[actionId] = `/web/image/menu.configurator/${tile.id}/icon`;
                    }
                }
            }
        } catch (error) {
            console.error("Menu Configurator: could not load app grid configuration", error);
        }

        patch(menu, {
            getApps() {
                const apps = super.getApps();
                if (!allowedActionIds || !allowedActionIds.length) {
                    return apps;
                }
                const appByActionId = new Map(apps.map((app) => [app.actionID, app]));
                const filtered = [];
                for (const actionId of allowedActionIds) {
                    const app = appByActionId.get(actionId);
                    if (app) {
                        if (iconByActionId[actionId]) {
                            app.webIconData = iconByActionId[actionId];
                        }
                        filtered.push(app);
                    }
                }
                // Safety net: if none of the configured actions match a real
                // top-level app, fall back to the full list instead of
                // leaving the Apps menu empty.
                return filtered.length ? filtered : apps;
            },
        });
    },
};

registry.category("services").add("menu_configurator_filter", menuConfiguratorFilterService);

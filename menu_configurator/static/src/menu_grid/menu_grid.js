/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class MenuConfiguratorGrid extends Component {
    static template = "menu_configurator.MenuGrid";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ tiles: [], stack: [] });

        onWillStart(async () => {
            this.state.tiles = await this.orm.searchRead(
                "menu.configurator",
                [["active", "=", true]],
                ["name", "action_id", "parent_id"],
                { order: "sequence asc" }
            );
        });
    }

    get currentParentId() {
        return this.state.stack.length
            ? this.state.stack[this.state.stack.length - 1].id
            : false;
    }

    get visibleTiles() {
        const parentId = this.currentParentId;
        return this.state.tiles.filter(
            (tile) => (tile.parent_id ? tile.parent_id[0] : false) === parentId
        );
    }

    hasChildren(tile) {
        return this.state.tiles.some((t) => t.parent_id && t.parent_id[0] === tile.id);
    }

    openTile(tile) {
        if (this.hasChildren(tile)) {
            this.state.stack.push(tile);
        } else if (tile.action_id) {
            this.action.doAction(tile.action_id[0]);
        }
    }

    goBack() {
        this.state.stack.pop();
    }

    goToRoot() {
        this.state.stack.splice(0, this.state.stack.length);
    }
}

registry.category("actions").add("menu_configurator_grid", MenuConfiguratorGrid);

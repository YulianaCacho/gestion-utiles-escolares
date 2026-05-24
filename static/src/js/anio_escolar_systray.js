/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class AnioEscolarSystray extends Component {
    static template = "gestion_utiles_escolares.AnioEscolarSystray";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            open: false,
            anios: [],
            current_id: false,
            current_name: "Año escolar",
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }


    async loadData() {
        const data = await this.orm.call("anio.escolar", "get_selector_data", []);

        this.state.anios = data.anios || [];
        this.state.current_id = data.current_id || false;
        this.state.current_name = data.current_name || "Año escolar";
    }

    toggleDropdown() {
        this.state.open = !this.state.open;
    }

    async seleccionarAnio(anioId) {
        await this.orm.call("anio.escolar", "cambiar_anio_escolar", [anioId]);

        await this.loadData();

        this.state.open = false;

        this.notification.add(`Se cambió a ${this.state.current_name}`, {
            type: "success",
        });

        window.location.reload();
    }

    abrirGestionAnios() {
        this.state.open = false;

        this.action.doAction({
           type: "ir.actions.act_window",
           name: "Años escolares",
           res_model: "anio.escolar",
           views: [[false, "list"], [false, "form"]],
           target: "current",
       });
   }

    abrirNuevoAnio() {
        this.state.open = false;

        this.action.doAction({
           type: "ir.actions.act_window",
           name: "Agregar nuevo año escolar",
           res_model: "anio.escolar",
           views: [[false, "form"]],
           target: "current",
           context: {
               default_estado: "borrador",
           },
        });
   }
}

registry.category("systray").add(
    "gestion_utiles_escolares.AnioEscolarSystray",
    {
        Component: AnioEscolarSystray,
    },
    {
        sequence: 90,
    }
);
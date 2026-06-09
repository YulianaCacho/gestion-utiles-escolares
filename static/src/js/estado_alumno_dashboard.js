/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

class EstadoAlumnoDashboard extends Component {
    static template = "gestion_utiles_escolares.EstadoAlumnoDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            loading: true,
            search: "",
            viewMode: "card",
            rows: [],
        });

        onWillStart(async () => {
            await this.loadDashboard();
        });
    }

    async loadDashboard() {
        this.state.loading = true;

        try {
            const data = await this.orm.call(
                "matricula.escolar",
                "get_estado_alumno_dashboard",
                [],
                {
                    search: this.state.search,
                }
            );

            this.state.rows = data.rows || [];

        } catch (error) {
            console.error(error);
            this.notification.add("No se pudo cargar Estado por alumno.", {
                type: "danger",
            });
        } finally {
            this.state.loading = false;
        }
    }

    onSearchInput(ev) {
        this.state.search = ev.target.value || "";
    }

    async onSearchKeydown(ev) {
        if (ev.key === "Enter") {
            await this.loadDashboard();
        }
    }

    setViewMode(mode) {
        this.state.viewMode = mode;
    }

    openNew() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Nueva matrícula",
            res_model: "matricula.escolar",
            views: [[false, "form"]],
            target: "current",
            context: {
                default_estado: "activo",
            },
        });
    }

    openForm(id) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Estado por alumno",
            res_model: "matricula.escolar",
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("estado_alumno_dashboard", EstadoAlumnoDashboard);
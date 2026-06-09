/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

class MatriculaDashboard extends Component {
    static template = "gestion_utiles_escolares.MatriculaDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            loading: true,
            search: "",
            titulo: "Lista de matrícula",
            subtitulo: "",
            stats: {
                total_estudiantes: 0,
                grados_activos: 0,
                matriculas_activas: 0,
            },
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
                "get_matriculas_dashboard",
                [],
                { search: this.state.search }
            );

            this.state.titulo = data.titulo || "Lista de matrícula";
            this.state.subtitulo = data.subtitulo || "";
            this.state.stats = data.stats || {};
            this.state.rows = data.rows || [];
        } catch (error) {
            this.notification.add("No se pudo cargar la lista de matrícula.", {
                type: "danger",
            });
        } finally {
            this.state.loading = false;
        }
    }

    async onSearchInput(ev) {
        this.state.search = ev.target.value || "";
    }

    async onSearchKeydown(ev) {
        if (ev.key === "Enter") {
            await this.loadDashboard();
        }
    }

    async doSearch() {
        await this.loadDashboard();
    }

    openForm(id) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "matricula.escolar",
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openNew() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "matricula.escolar",
            views: [[false, "form"]],
            target: "current",
        });
    }

    openManageRecords() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Gestionar registros",
            res_model: "matricula.escolar",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            target: "current",
        });
    }
}

registry.category("actions").add("matricula_dashboard", MatriculaDashboard);
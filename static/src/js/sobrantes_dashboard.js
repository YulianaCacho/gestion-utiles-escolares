/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

class SobrantesDashboard extends Component {
    static template = "gestion_utiles_escolares.SobrantesDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        this.searchTimer = null;

        this.state = useState({
            loading: true,
            search: "",
            titulo: "Sobrantes del año anterior",
            stats: {
                total_productos: 0,
                unidades_disponibles: 0,
                disponibles: 0,
                anio_destino: "",
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
                "sobrante.utiles.anio",
                "get_sobrantes_dashboard",
                [],
                {
                    search: this.state.search,
                }
            );

            this.state.titulo = data.titulo || "Sobrantes del año anterior";
            this.state.stats = data.stats || {};
            this.state.rows = data.rows || [];

        } catch (error) {
            console.error(error);
            this.notification.add("No se pudo cargar los sobrantes del año anterior.", {
                type: "danger",
            });
        } finally {
            this.state.loading = false;
        }
    }

    onSearchInput(ev) {
        this.state.search = ev.target.value || "";

        if (this.searchTimer) {
            clearTimeout(this.searchTimer);
        }

        this.searchTimer = setTimeout(async () => {
            await this.loadDashboard();
        }, 350);
    }

    async onSearchKeydown(ev) {
        if (ev.key === "Enter") {
            await this.loadDashboard();
        }
    }

    openForm(id) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Sobrante del año anterior",
            res_model: "sobrante.utiles.anio",
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("sobrantes_dashboard", SobrantesDashboard);
/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

class ListaUtilesDashboard extends Component {
    static template = "gestion_utiles_escolares.ListaUtilesDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            loading: true,
            search: "",
            titulo: "Lista de útiles por grado",
            subtitulo: "",
            stats: {
                total_listas: 0,
                total_utiles: 0,
                promedio_grado: 0,
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
                "lista.utiles.grado",
                "get_lista_utiles_dashboard",
                [],
                {
                    search: this.state.search,
                }
            );

            this.state.titulo = data.titulo || "Lista de útiles por grado";
            this.state.subtitulo = data.subtitulo || "";
            this.state.stats = data.stats || {
                total_listas: 0,
                total_utiles: 0,
                promedio_grado: 0,
            };
            this.state.rows = data.rows || [];
        } catch (error) {
            console.error(error);
            this.notification.add("No se pudo cargar la lista de útiles por grado.", {
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

    async doSearch() {
        await this.loadDashboard();
    }

    openForm(id) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Lista de útiles por grado",
            res_model: "lista.utiles.grado",
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openNew() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Nueva lista de útiles",
            res_model: "lista.utiles.grado",
            views: [[false, "form"]],
            target: "current",
        });
    }

    openManageRecords() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Gestionar listas de útiles",
            res_model: "lista.utiles.grado",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            target: "current",
        });
    }

    exportCsv() {
        const rows = this.state.rows || [];

        if (!rows.length) {
            this.notification.add("No hay listas para exportar.", {
                type: "warning",
            });
            return;
        }

        const headers = [
            "Nombre de la lista",
            "Año escolar",
            "Grado escolar",
            "Cantidad de productos",
        ];

        const escapeCsv = (value) => {
            const text = String(value ?? "");
            return `"${text.replace(/"/g, '""')}"`;
        };

        const csvRows = [
            headers.map(escapeCsv).join(","),
            ...rows.map((row) => [
                row.name,
                row.anio,
                row.grado,
                row.cantidad,
            ].map(escapeCsv).join(",")),
        ];

        const blob = new Blob(["\ufeff" + csvRows.join("\n")], {
            type: "text/csv;charset=utf-8;",
        });

        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");

        link.href = url;
        link.download = "lista_utiles_por_grado.csv";
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);

        this.notification.add("Exportación generada correctamente.", {
            type: "success",
        });
    }
}

registry.category("actions").add("lista_utiles_dashboard", ListaUtilesDashboard);
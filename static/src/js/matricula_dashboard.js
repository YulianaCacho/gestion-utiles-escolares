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
            showConfigMenu: false,
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
                {
                    search: this.state.search,
                }
            );

            this.state.titulo = data.titulo || "Lista de matrícula";
            this.state.subtitulo = data.subtitulo || "";
            this.state.stats = data.stats || {
                total_estudiantes: 0,
                grados_activos: 0,
                matriculas_activas: 0,
            };
            this.state.rows = data.rows || [];

        } catch (error) {
            console.error(error);
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
            name: "Matrícula",
            res_model: "matricula.escolar",
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openNew() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Nueva matrícula",
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

    toggleConfigMenu(ev) {
        if (ev) {
            ev.stopPropagation();
        }

        this.state.showConfigMenu = !this.state.showConfigMenu;
    }

    importarRegistros(ev) {
        if (ev) {
            ev.stopPropagation();
        }

        this.state.showConfigMenu = false;

        this.action.doAction({
            type: "ir.actions.client",
            tag: "import",
            name: "Importar matrículas",
            params: {
                model: "matricula.escolar",
                context: {
                    active_model: "matricula.escolar",
                },
            },
        });
    }

    exportarTodo(ev) {
        if (ev) {
            ev.stopPropagation();
        }

        this.state.showConfigMenu = false;

        const rows = this.state.rows || [];

        if (!rows.length) {
            this.notification.add("No hay registros para exportar.", {
                type: "warning",
            });
            return;
        }

        const headers = [
            "Estudiante",
            "Grado escolar",
            "Apoderado principal",
            "Estado",
        ];

        const escapeCsv = (value) => {
            const text = String(value || "");
            return `"${text.replace(/"/g, '""')}"`;
        };

        const csvRows = [
            headers.map(escapeCsv).join(","),
            ...rows.map((row) => [
                row.estudiante,
                row.grado,
                row.apoderado_principal,
                row.estado,
            ].map(escapeCsv).join(",")),
        ];

        const csvContent = csvRows.join("\n");
        const blob = new Blob(["\ufeff" + csvContent], {
            type: "text/csv;charset=utf-8;",
        });

        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");

        link.href = url;
        link.download = "lista_matricula.csv";
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        URL.revokeObjectURL(url);

        this.notification.add("Exportación generada correctamente.", {
            type: "success",
        });
    }
}

registry.category("actions").add("matricula_dashboard", MatriculaDashboard);
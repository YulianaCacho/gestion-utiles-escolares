/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

function normalizeText(value) {
    return String(value || "")
        .toLowerCase()
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .trim();
}

function inferNivel(grado) {
    const g = normalizeText(grado);
    if (
        g.includes("inicial") ||
        g.includes("3 años") ||
        g.includes("4 años") ||
        g.includes("5 años")
    ) {
        return "Inicial";
    }
    return "Primaria";
}

function inferEstado(estado, avance) {
    const e = normalizeText(estado);

    if (e.includes("completo") || avance >= 100) {
        return "Completo";
    }
    return "Incompleto";
}

class ReporteRecepcionDashboard extends Component {
    static template = "gestion_utiles_escolares.ReporteRecepcionDashboard";

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");

        this.state = useState({
            search: "",
            filterMode: "Todos", // Todos | Completos | Incompletos | Inicial | Primaria
            yearLabel: "2026",
            rows: [],
            selectedIds: [],
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        // IMPORTANTE:
        // Si alguno de estos nombres de campo en tu modelo es distinto,
        // solo cámbialo aquí.
        const records = await this.orm.searchRead(
            "recepcion.utiles.escolar",
            [],
            [
                "name",
                "estudiante_id",
                "grado_escolar",
                "lista_utiles_id",
                "estado",
                "cantidad_total",
                "cantidad_completada",
                "porcentaje_avance",
            ],
            { limit: 500, order: "id desc" }
        );

        const mapped = records.map((rec) => {
            const estudiante = rec.estudiante_id ? rec.estudiante_id[1] : "Sin estudiante";
            const grado = rec.grado_escolar || "Sin grado";
            const lista = rec.lista_utiles_id ? rec.lista_utiles_id[1] : "Sin lista";

            const total = Number(rec.cantidad_total || 0);
            const completado = Number(rec.cantidad_completada || 0);

            const avance =
                rec.porcentaje_avance !== false &&
                rec.porcentaje_avance !== null &&
                rec.porcentaje_avance !== undefined
                    ? Number(rec.porcentaje_avance)
                    : total > 0
                    ? Math.round((completado / total) * 100)
                    : 0;

            const estado = inferEstado(rec.estado, avance);
            const nivel = inferNivel(grado);

            return {
                id: rec.id,
                estudiante,
                grado,
                lista,
                total,
                completado,
                avance,
                estado,
                nivel,
            };
        });

        this.state.rows = mapped;

        // seleccionar por defecto las primeras 2, para que se vea parecido a tu ejemplo
        this.state.selectedIds = mapped.slice(0, 2).map((r) => r.id);
    }

    get filteredRows() {
        const text = normalizeText(this.state.search);

        return this.state.rows.filter((row) => {
            const matchesText =
                !text ||
                normalizeText(row.estudiante).includes(text) ||
                normalizeText(row.grado).includes(text) ||
                normalizeText(row.lista).includes(text);

            let matchesFilter = true;

            if (this.state.filterMode === "Completos") {
                matchesFilter = row.estado === "Completo";
            } else if (this.state.filterMode === "Incompletos") {
                matchesFilter = row.estado === "Incompleto";
            } else if (this.state.filterMode === "Inicial") {
                matchesFilter = row.nivel === "Inicial";
            } else if (this.state.filterMode === "Primaria") {
                matchesFilter = row.nivel === "Primaria";
            }

            return matchesText && matchesFilter;
        });
    }

    get selectedCount() {
        return this.state.selectedIds.length;
    }

    setFilter(mode) {
        this.state.filterMode = mode;
    }

    isSelected(id) {
        return this.state.selectedIds.includes(id);
    }

    toggleOne(id) {
        if (this.isSelected(id)) {
            this.state.selectedIds = this.state.selectedIds.filter((x) => x !== id);
        } else {
            this.state.selectedIds = [...this.state.selectedIds, id];
        }
    }

    toggleAll(ev) {
        if (ev.target.checked) {
            this.state.selectedIds = this.filteredRows.map((row) => row.id);
        } else {
            this.state.selectedIds = [];
        }
    }

    progressStyle(row) {
        const pct = Math.max(0, Math.min(100, Number(row.avance || 0)));
        return `width: ${pct}%;`;
    }

    statusClass(estado) {
        return estado === "Completo"
            ? "o_rr_estado o_rr_estado_ok"
            : "o_rr_estado o_rr_estado_warn";
    }

    openFilters() {
        this.notification.add("Aquí luego podemos conectar más filtros si deseas.", {
            type: "info",
        });
    }

    generatePdf() {
        this.notification.add(
            "La vista ya quedó visual. Si quieres, luego conectamos este botón a tu PDF real.",
            { type: "info" }
        );
    }
}

registry
    .category("actions")
    .add("gestion_utiles_escolares.reporte_recepcion_dashboard", ReporteRecepcionDashboard);
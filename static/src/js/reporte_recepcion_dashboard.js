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

function getMany2oneValue(record, fieldName) {
    const value = record[fieldName];

    if (Array.isArray(value)) {
        return value[1] || "";
    }

    return value || "";
}

function firstExistingValue(record, fields) {
    for (const field of fields) {
        const value = record[field];

        if (Array.isArray(value) && value[1]) {
            return value[1];
        }

        if (value !== false && value !== null && value !== undefined && value !== "") {
            return value;
        }
    }

    return "";
}

function inferNivel(grado) {
    const g = normalizeText(grado);

    if (
        g.includes("inicial") ||
        g.includes("3 anos") ||
        g.includes("4 anos") ||
        g.includes("5 anos")
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
            filterMode: "Todos",
            yearLabel: "2026",
            rows: [],
            selectedIds: [],
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        const model = "recepcion.utiles.escolar";

        const fieldsInfo = await this.orm.call(
            model,
            "fields_get",
            [],
            { attributes: ["string", "type"] }
        );

        const possibleFields = [
            "name",
            "codigo_recepcion",

            "estudiante_id",
            "alumno_id",
            "student_id",

            "grado_escolar",
            "grado_id",
            "grado",

            "lista_utiles_id",
            "lista_utiles_grado_id",
            "lista_id",

            "estado",
            "state",

            "cantidad_total",
            "total",
            "total_utiles",
            "cantidad_esperada",

            "cantidad_completada",
            "cantidad_entregada",
            "completado",
            "utiles_recibidos",

            "porcentaje_avance",
            "avance",
            "progreso",
        ];

        const existingFields = possibleFields.filter((field) => fieldsInfo[field]);

        const records = await this.orm.searchRead(
            model,
            [],
            existingFields,
            { limit: 500, order: "id desc" }
        );

        const mapped = records.map((rec) => {
            const estudiante =
                firstExistingValue(rec, ["estudiante_id", "alumno_id", "student_id"]) ||
                firstExistingValue(rec, ["name", "codigo_recepcion"]) ||
                "Sin estudiante";

            const grado =
                firstExistingValue(rec, ["grado_escolar", "grado_id", "grado"]) ||
                "Sin grado";

            const lista =
                firstExistingValue(rec, [
                    "lista_utiles_id",
                    "lista_utiles_grado_id",
                    "lista_id",
                ]) || "Lista 2026";

            const total = Number(
                firstExistingValue(rec, [
                    "cantidad_total",
                    "total",
                    "total_utiles",
                    "cantidad_esperada",
                ]) || 0
            );

            const completado = Number(
                firstExistingValue(rec, [
                    "cantidad_completada",
                    "cantidad_entregada",
                    "completado",
                    "utiles_recibidos",
                ]) || 0
            );

            let avance = Number(
                firstExistingValue(rec, [
                    "porcentaje_avance",
                    "avance",
                    "progreso",
                ]) || 0
            );

            if (!avance && total > 0) {
                avance = Math.round((completado / total) * 100);
            }

            const estadoRaw = firstExistingValue(rec, ["estado", "state"]);
            const estado = inferEstado(estadoRaw, avance);
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
        this.state.selectedIds = mapped.slice(0, 2).map((row) => row.id);
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
        const ids = [...this.state.selectedIds];

        if (!ids.length) {
           this.notification.add(
               "Selecciona al menos una recepción para generar el PDF.",
               { type: "warning" }
           );
           return;
       }

       const url = `/report/pdf/gestion_utiles_escolares.report_recepciones_pdf_template/${ids.join(",")}`;
       window.open(url, "_blank");
    }
}

registry
    .category("actions")
    .add("gestion_utiles_escolares.reporte_recepcion_dashboard", ReporteRecepcionDashboard);
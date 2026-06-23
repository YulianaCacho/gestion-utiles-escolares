/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class ReporteAlmacenMovimientos extends Component {
    static template = "gestion_utiles_escolares.ReporteAlmacenMovimientos";

    setup() {
        this.orm = useService("orm");

        const today = new Date();
        const year = today.getFullYear();
        const month = String(today.getMonth() + 1).padStart(2, "0");

        this.state = useState({
            loading: true,
            monthLabel: "",
            monthShort: "",
            selectedMonth: `${year}-${month}`,
            kpis: {
                entradas: "0",
                salidas: "0",
                ajustes: 0,
                balance: "0",
            },
            events: [],
            grados: [],
            responsables: [],
            gradoSeleccionado: "",
            responsableSeleccionado: "",
            anioEscolarId: false,
        });

        onWillStart(async () => {
            await this.loadCurrentYear();
            await this.loadData();
        });
    }

    async loadCurrentYear() {
        const anioData = await this.orm.call("anio.escolar", "get_selector_data", []);
        this.state.anioEscolarId = anioData.current_id || false;
    }

    async loadData() {
        this.state.loading = true;

        await this.loadCurrentYear();

        let year = null;
        let month = null;

        if (this.state.selectedMonth) {
            const parts = this.state.selectedMonth.split("-");
            year = parseInt(parts[0], 10);
            month = parseInt(parts[1], 10);
        }

        const data = await this.orm.call(
            "almacen.utiles.movimiento",
            "get_reporte_almacen_movimientos",
            [],
            {
                month: month,
                year: year,
                grado: this.state.gradoSeleccionado || false,
                responsable_id: this.state.responsableSeleccionado || false,
                anio_escolar_id: this.state.anioEscolarId || false,
            }
        );

        this.state.monthLabel = data.month_label;
        this.state.monthShort = data.month_short;
        this.state.kpis = data.kpis;
        this.state.events = data.events;
        this.state.grados = data.grados || [];
        this.state.responsables = data.responsables || [];
        this.state.loading = false;
    }

    async onChangeMonth(ev) {
        this.state.selectedMonth = ev.target.value;
        await this.loadData();
    }

    async onChangeGrado(ev) {
        this.state.gradoSeleccionado = ev.target.value;
        await this.loadData();
    }

    async onChangeResponsable(ev) {
        this.state.responsableSeleccionado = ev.target.value;
        await this.loadData();
    }

    async exportPdf() {
        let anchorId = false;

        if (this.state.events && this.state.events.length > 0) {
            for (const ev of this.state.events) {
                const match = String(ev.id || "").match(/\d+/);
                if (match) {
                    anchorId = match[0];
                    break;
                }
            }
        }

        if (!anchorId) {
            const movs = await this.orm.search(
                "almacen.utiles.movimiento",
                [],
                { limit: 1 }
            );
            anchorId = movs.length ? movs[0] : false;
        }

        if (!anchorId) {
            alert("No hay datos disponibles para exportar en el período seleccionado.");
            return;
        }

        let year = null;
        let month = null;

        if (this.state.selectedMonth) {
            const parts = this.state.selectedMonth.split("-");
            year = parseInt(parts[0], 10);
            month = parseInt(parts[1], 10);
        }

        const ctx = {
            month: month,
            year: year,
            grado: this.state.gradoSeleccionado || false,
            responsable_id: this.state.responsableSeleccionado
                ? parseInt(this.state.responsableSeleccionado, 10)
                : false,
            anio_escolar_id: this.state.anioEscolarId || false,
        };

        const ctxEncoded = encodeURIComponent(JSON.stringify(ctx));
        const url = `/report/pdf/gestion_utiles_escolares.report_almacen_movimientos_pdf_document/${anchorId}?context=${ctxEncoded}`;
        window.open(url, "_blank");
    }
}

registry
    .category("actions")
    .add("gestion_utiles_escolares.reporte_almacen_movimientos", ReporteAlmacenMovimientos);
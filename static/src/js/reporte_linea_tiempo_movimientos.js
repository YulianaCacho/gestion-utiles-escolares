/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class ReporteLineaTiempoMovimientos extends Component {
    static template = "gestion_utiles_escolares.ReporteLineaTiempoMovimientos";

    setup() {
        this.orm = useService("orm");
        this.searchTimer = null;

        const today = new Date();
        const year = today.getFullYear();
        const month = String(today.getMonth() + 1).padStart(2, "0");

        this.state = useState({
            selectedMonth: `${year}-${month}`,
            monthLabel: "",
            search: "",
            tipoSeleccionado: "",
            gradoSeleccionado: "",
            responsableSeleccionado: "",
            total: 0,
            rows: [],
            grados: [],
            responsables: [],
            kpis: {
                entradas: "0",
                salidas: "0",
                ajustes: 0,
                balance: "0",
            },
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
            "get_linea_tiempo_movimientos",
            [],
            {
                month: month,
                year: year,
                tipo: this.state.tipoSeleccionado || false,
                search: this.state.search || false,
                grado: this.state.gradoSeleccionado || false,
                responsable_id: this.state.responsableSeleccionado || false,
                anio_escolar_id: this.state.anioEscolarId || false,
            }
        );

        this.state.monthLabel = data.month_label || "";
        this.state.total = data.total || 0;
        this.state.rows = data.rows || [];
        this.state.kpis = data.kpis || {
            entradas: "0",
            salidas: "0",
            ajustes: 0,
            balance: "0",
        };
        this.state.grados = data.grados || [];
        this.state.responsables = data.responsables || [];
    }

    async onChangeMonth(ev) {
        this.state.selectedMonth = ev.target.value;
        await this.loadData();
    }

    async onChangeTipo(ev) {
        this.state.tipoSeleccionado = ev.target.value;
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

    onInputSearch(ev) {
        this.state.search = ev.target.value;

        if (this.searchTimer) {
            clearTimeout(this.searchTimer);
        }

        this.searchTimer = setTimeout(async () => {
            await this.loadData();
        }, 350);
    }

    async clearTipo() {
        this.state.tipoSeleccionado = "";
        await this.loadData();
    }

    async setTipo(tipo) {
        this.state.tipoSeleccionado = tipo;
        await this.loadData();
    }

    exportPdf() {
        window.print();
    }
}

registry
    .category("actions")
    .add("gestion_utiles_escolares.reporte_linea_tiempo_movimientos", ReporteLineaTiempoMovimientos);
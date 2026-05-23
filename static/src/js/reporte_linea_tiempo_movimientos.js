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
            total: 0,
            rows: [],
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
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
            }
        );

        this.state.monthLabel = data.month_label;
        this.state.total = data.total;
        this.state.rows = data.rows || [];
    }

    async onChangeMonth(ev) {
        this.state.selectedMonth = ev.target.value;
        await this.loadData();
    }

    async onChangeTipo(ev) {
        this.state.tipoSeleccionado = ev.target.value;
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
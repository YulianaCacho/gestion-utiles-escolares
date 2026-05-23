/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class ReporteAlmacenMovimientos extends Component {
    static template = "gestion_utiles_escolares.ReporteAlmacenMovimientos";

    setup() {
        this.orm = useService("orm");

        this.state = useState({
            loading: true,
            monthLabel: "",
            monthShort: "",
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
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        this.state.loading = true;

        const data = await this.orm.call(
            "almacen.utiles.movimiento",
            "get_reporte_almacen_movimientos",
            [],
            {
                grado: this.state.gradoSeleccionado || false,
                responsable_id: this.state.responsableSeleccionado || false,
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

    async onChangeGrado(ev) {
        this.state.gradoSeleccionado = ev.target.value;
        await this.loadData();
    }

    async onChangeResponsable(ev) {
        this.state.responsableSeleccionado = ev.target.value;
        await this.loadData();
    }

    exportPdf() {
        window.print();
    }
}

registry
    .category("actions")
    .add("gestion_utiles_escolares.reporte_almacen_movimientos", ReporteAlmacenMovimientos);
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
            {}
        );

        this.state.monthLabel = data.month_label;
        this.state.monthShort = data.month_short;
        this.state.kpis = data.kpis;
        this.state.events = data.events;
        this.state.loading = false;
    }

    exportPdf() {
        window.print();
    }
}

registry
    .category("actions")
    .add("gestion_utiles_escolares.reporte_almacen_movimientos", ReporteAlmacenMovimientos);
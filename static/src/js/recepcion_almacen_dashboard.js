/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class RecepcionAlmacenDashboard extends Component {
    static template = "gestion_utiles_escolares.RecepcionAlmacenDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        this.searchTimer = null;

        this.state = useState({
            modo: "lista",
            search: "",
            filtroEstado: "todos",
            total: 0,
            rows: [],
            detalle: null,
            selectedIds: [],
        });

        onWillStart(async () => {
            await this.loadList();
        });
    }

    async loadList() {
        const data = await this.orm.call(
            "recepcion.utiles.escolar",
            "get_recepciones_almacen_dashboard",
            [],
            {
                search: this.state.search || false,
                estado: this.state.filtroEstado || "todos",
            }
        );

        this.state.total = data.total || 0;
        this.state.rows = data.rows || [];

        const idsVisibles = new Set(this.state.rows.map((row) => row.id));
        this.state.selectedIds = this.state.selectedIds.filter((id) => idsVisibles.has(id));
    }

    async openDetalle(id) {
        const data = await this.orm.call(
            "recepcion.utiles.escolar",
            "get_recepcion_almacen_detalle",
            [],
            {
                recepcion_id: id,
            }
        );

        this.state.detalle = data;
        this.state.modo = "detalle";
    }

    async volverLista() {
        this.state.modo = "lista";
        this.state.detalle = null;
        await this.loadList();
    }

    async nuevaRecepcion() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: "Nueva recepción",
            res_model: "recepcion.utiles.escolar",
            views: [[false, "form"]],
            target: "current",
            context: {
                form_view_ref: "gestion_utiles_escolares.view_recepcion_utiles_escolar_form_limpio_almacen",
        },
    });
}

    onInputSearch(ev) {
        this.state.search = ev.target.value;

        if (this.searchTimer) {
            clearTimeout(this.searchTimer);
        }

        this.searchTimer = setTimeout(async () => {
            await this.loadList();
        }, 350);
    }

    async setFiltro(estado) {

        this.state.filtroEstado = estado;
        await this.loadList();
    }

isSelected(id) {
    return this.state.selectedIds.includes(id);
}

isAllSelected() {
    return this.state.rows.length > 0 &&
        this.state.rows.every((row) => this.state.selectedIds.includes(row.id));
}

toggleSelect(id, ev) {
    id = Number(id);

    if (ev.target.checked) {
        if (!this.state.selectedIds.includes(id)) {
            this.state.selectedIds = [...this.state.selectedIds, id];
        }
    } else {
        this.state.selectedIds = this.state.selectedIds.filter((item) => item !== id);
    }
}

toggleSelectAll(ev) {
    if (ev.target.checked) {
        this.state.selectedIds = this.state.rows.map((row) => row.id);
    } else {
        this.state.selectedIds = [];
    }
}

async borrarSeleccionados() {
    const ids = [...this.state.selectedIds];

    if (!ids.length) {
        return;
    }

    const confirmar = window.confirm(
        `¿Seguro que deseas borrar ${ids.length} recepción(es) seleccionada(s)?`
    );

    if (!confirmar) {
        return;
    }

    try {
        const result = await this.orm.call(
            "recepcion.utiles.escolar",
            "borrar_recepciones_almacen_dashboard",
            [ids]
        );

        this.state.selectedIds = [];

        this.notification.add(
            `Se borraron ${result.deleted || 0} recepción(es).`,
            { type: "success" }
        );

        await this.loadList();

    } catch (error) {
        this.notification.add(
            "No se pudo borrar. Revisa si la recepción ya fue validada o tiene movimientos de almacén.",
            { type: "danger" }
        );
    }
}


    onChangeCantidad(lineaId, ev) {
        const value = ev.target.value;

        if (!this.state.detalle || !this.state.detalle.lineas) {
            return;
        }

        const linea = this.state.detalle.lineas.find((item) => item.id === lineaId);

        if (linea) {
            linea.cantidad_recibida = value;
        }
    }

    getLineasParaGuardar() {
        if (!this.state.detalle || !this.state.detalle.lineas) {
            return [];
        }

        return this.state.detalle.lineas.map((linea) => ({
            id: linea.id,
            cantidad_recibida: linea.cantidad_recibida || 0,
        }));
    }

    async guardar() {
        await this.orm.call(
            "recepcion.utiles.escolar",
            "guardar_recepcion_almacen_dashboard",
            [],
            {
                recepcion_id: this.state.detalle.id,
                lineas: this.getLineasParaGuardar(),
            }
        );

        this.notification.add("Recepción guardada correctamente.", {
            type: "success",
        });

        await this.openDetalle(this.state.detalle.id);
    }

    async validarRecepcion() {
        await this.orm.call(
            "recepcion.utiles.escolar",
            "validar_recepcion_almacen_dashboard",
            [],
            {
                recepcion_id: this.state.detalle.id,
                lineas: this.getLineasParaGuardar(),
            }
        );

        this.notification.add("Recepción validada correctamente.", {
            type: "success",
        });

        await this.openDetalle(this.state.detalle.id);
    }
}

registry
    .category("actions")
    .add("gestion_utiles_escolares.recepcion_almacen_dashboard", RecepcionAlmacenDashboard);
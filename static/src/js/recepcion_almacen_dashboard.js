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

   async gestionarRegistros() {
    await this.action.doAction({
        type: "ir.actions.act_window",
        name: "Gestionar recepciones",
        res_model: "recepcion.utiles.escolar",
        views: [[false, "list"], [false, "form"]],
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

    editarRecepcion(row, ev = null) {
        if (ev) {
            ev.stopPropagation();
        }

        if (!row || !row.id) {
            return;
        }

        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Editar recepción",
            res_model: "recepcion.utiles.escolar",
            res_id: row.id,
            views: [[false, "form"]],
            target: "current",
        });
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
    
    async enviarAlmacen() {
        if (!this.state.detalle || !this.state.detalle.id) {
           return;
       }

       try {
            const result = await this.orm.call(
                "recepcion.utiles.escolar",
                "enviar_recepcion_almacen_dashboard",
                [],
               {
                   recepcion_id: this.state.detalle.id,
               }
         );

        this.notification.add(result.message || "Proceso realizado.", {
            type: result.success ? "success" : "warning",
        });

        await this.openDetalle(this.state.detalle.id);

    } catch (error) {
        this.notification.add(
            "No se pudo enviar al almacén. Revisa si la recepción ya fue validada o si tiene productos para almacén.",
            { type: "danger" }
        );
      }
    }

}

registry
    .category("actions")
    .add("gestion_utiles_escolares.recepcion_almacen_dashboard", RecepcionAlmacenDashboard);
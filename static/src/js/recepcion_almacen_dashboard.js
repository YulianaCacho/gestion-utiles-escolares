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

    const actionContext = this.props.action?.context || {};
    this.initialRecepcionId =
      actionContext.open_recepcion_id || actionContext.recepcion_id || false;

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

      if (this.initialRecepcionId) {
        await this.openDetalle(this.initialRecepcionId);
      }
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
      },
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
      },
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
        form_view_ref:
          "gestion_utiles_escolares.view_recepcion_utiles_escolar_form_limpio_almacen",
      },
    });
  }

  async gestionarRegistros() {
    await this.action.doAction({
      type: "ir.actions.act_window",
      name: "Gestionar recepciones",
      res_model: "recepcion.utiles.escolar",
      views: [
        [false, "list"],
        [false, "form"],
      ],
      target: "current",
      context: {
        form_view_ref:
          "gestion_utiles_escolares.view_recepcion_utiles_escolar_form_limpio_almacen",
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
    if (!this.state.detalle || !this.state.detalle.lineas) {
      return;
    }

    const linea = this.state.detalle.lineas.find((item) => item.id === lineaId);

    if (!linea) {
      return;
    }

    const valorIngresado = ev.target.value;

    // Permitir que el campo quede vacío
    // mientras el usuario está escribiendo
    if (valorIngresado === "") {
      linea.cantidad_recibida = "";
      return;
    }

    let cantidad = Number(String(valorIngresado).replace(",", "."));

    const cantidadMaxima = Number(linea.cantidad_maxima || 0);

    // Validar número incorrecto
    if (!Number.isFinite(cantidad)) {
      cantidad = 0;

      this.notification.add(
        `La cantidad de "${linea.producto}" ` + "debe ser un número válido.",
        {
          type: "warning",
        },
      );
    }

    // No permitir números decimales,
    // incluso si fueron pegados
    else if (!Number.isInteger(cantidad)) {
      this.notification.add(
        `La cantidad de "${linea.producto}" ` + "debe ser un número entero.",
        {
          type: "warning",
        },
      );

      ev.target.value = linea.cantidad_recibida || 0;

      return;
    }

    // No permitir números negativos
    else if (cantidad < 0) {
      cantidad = 0;

      this.notification.add(
        `No se permiten cantidades negativas ` + `para "${linea.producto}".`,
        {
          type: "warning",
        },
      );
    }

    // No permitir superar la cantidad requerida
    else if (cantidad > cantidadMaxima) {
      cantidad = cantidadMaxima;

      this.notification.add(
        `La cantidad de "${linea.producto}" ` +
          `no puede ser mayor a ` +
          `${cantidadMaxima}.`,
        {
          type: "warning",
        },
      );
    }

    linea.cantidad_recibida = cantidad;

    ev.target.value = cantidad;
  }

  onKeydownCantidad(ev) {
    const teclasNoPermitidas = ["-", "+", "e", "E", ".", ","];

    if (teclasNoPermitidas.includes(ev.key)) {
      ev.preventDefault();
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

  async reconocerPorImagen() {
    if (!this.state.detalle || !this.state.detalle.id) {
      this.notification.add("Primero abre una recepción guardada.", {
        type: "warning",
      });
      return;
    }

    try {
      await this.orm.call(
        "recepcion.utiles.escolar",
        "guardar_recepcion_almacen_dashboard",
        [],
        {
          recepcion_id: this.state.detalle.id,
          lineas: this.getLineasParaGuardar(),
        },
      );

      await this.action.doAction({
        type: "ir.actions.client",
        name: "Reconocer por imagen",
        tag: "gestion_utiles_escolares.reconocimiento_ia_dashboard",
        target: "current",
        context: {
          active_id: this.state.detalle.id,
          active_model: "recepcion.utiles.escolar",
          recepcion_id: this.state.detalle.id,
          modo_recepcion: true,
          return_to_recepcion_dashboard: true,
        },
      });
    } catch (error) {
      this.notification.add(
        "No se pudo abrir el reconocimiento IA. Guarda la recepción e inténtalo nuevamente.",
        { type: "danger" },
      );
    }
  }

  async guardar() {
    await this.orm.call(
      "recepcion.utiles.escolar",
      "guardar_recepcion_almacen_dashboard",
      [],
      {
        recepcion_id: this.state.detalle.id,
        lineas: this.getLineasParaGuardar(),
      },
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
      },
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
        },
      );

      this.notification.add(result.message || "Proceso realizado.", {
        type: result.success ? "success" : "warning",
      });

      await this.openDetalle(this.state.detalle.id);
    } catch (error) {
      this.notification.add(
        "No se pudo enviar al almacén. Revisa si la recepción ya fue validada o si tiene productos para almacén.",
        { type: "danger" },
      );
    }
  }
}

registry
  .category("actions")
  .add(
    "gestion_utiles_escolares.recepcion_almacen_dashboard",
    RecepcionAlmacenDashboard,
  );

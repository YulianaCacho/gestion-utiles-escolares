from odoo import models, fields, api
from odoo.exceptions import UserError


class RecepcionUtilesEscolar(models.Model):
    _name = "recepcion.utiles.escolar"
    _description = "Recepción de útiles escolares"
    _rec_name = "name"
    _order = "fecha desc, id desc"

    def _fmt_qty_dashboard(self, value):
        value = float(value or 0)
        if value.is_integer():
            return str(int(value))
        return f"{value:.2f}".rstrip("0").rstrip(".")

    def _grado_label_dashboard(self, grado):
        info = self.fields_get(["grado_escolar"]).get("grado_escolar", {})
        selection = dict(info.get("selection", []))
        return selection.get(grado, grado or "")

    def _iniciales_dashboard(self, nombre):
        partes = (nombre or "").split()
        if not partes:
            return ""
        return "".join([p[0].upper() for p in partes[:2]])

    name = fields.Char(
        string="Código de recepción",
        default="Nueva",
        readonly=True,
        copy=False
    )

    fecha = fields.Date(
        string="Fecha de recepción",
        default=fields.Date.context_today,
        required=True
    )

    matricula_id = fields.Many2one(
        "matricula.escolar",
        string="Matrícula",
        domain="[('estado', '=', 'activo')]",
        ondelete="restrict"
    )

    estudiante_id = fields.Many2one(
        "res.partner",
        string="Estudiante",
        related="matricula_id.estudiante_id",
        store=True,
        readonly=True
    )

    anio = fields.Char(
        string="Año escolar",
        compute="_compute_datos_matricula",
        store=True,
        readonly=True
    )

    grado_escolar = fields.Selection(
        related="matricula_id.grado_escolar",
        string="Grado escolar",
        store=True,
        readonly=True
    )

    lista_id = fields.Many2one(
        "lista.utiles.grado",
        string="Lista de útiles",
        related="matricula_id.lista_utiles_id",
        store=True,
        readonly=True
    )

    recibido_por_id = fields.Many2one(
        "res.users",
        string="Recibido por",
        default=lambda self: self.env.user,
        readonly=True
    )

    linea_ids = fields.One2many(
        "recepcion.utiles.linea",
        "recepcion_id",
        string="Productos recibidos"
    )

    movimiento_almacen_ids = fields.One2many(
        "almacen.utiles.movimiento",
        "recepcion_id",
        string="Movimientos de almacén"
    )

    estado = fields.Selection(
        [
            ("borrador", "Borrador"),
            ("incompleto", "Incompleto"),
            ("completo", "Completo"),
            ("validado", "Validado"),
        ],
        string="Estado interno",
        default="borrador"
    )

    observacion = fields.Text(string="Observación general")

    total_productos = fields.Integer(
        string="Total de productos",
        compute="_compute_resumen",
        store=True
    )

    total_completos = fields.Integer(
        string="Productos completos",
        compute="_compute_resumen",
        store=True
    )

    total_faltantes = fields.Integer(
        string="Productos con faltantes",
        compute="_compute_resumen",
        store=True
    )

    porcentaje_avance = fields.Float(
        string="Porcentaje de avance",
        compute="_compute_resumen",
        store=True
    )

    estado_entrega = fields.Selection(
        [
            ("sin_cargar", "Sin cargar"),
            ("incompleto", "Incompleto"),
            ("completo", "Completo"),
        ],
        string="Estado de entrega",
        compute="_compute_resumen",
        store=True
    )

    items_resumen = fields.Char(
        string="Ítems",
        compute="_compute_items_resumen",
        store=True
    )

    estado_visual = fields.Selection(
        [
            ("pendiente", "Pendiente"),
            ("incompleto", "Incompleto"),
            ("listo", "Listo"),
        ],
        string="Estado",
        compute="_compute_estado_visual",
        store=True
    )

    estado_almacen = fields.Selection(
        [
            ("pendiente", "Pendiente"),
            ("parcial", "Envío parcial"),
            ("enviado", "Enviado a almacén"),
            ("sin_productos", "Sin productos para almacén"),
        ],
        string="Estado de almacén",
        compute="_compute_estado_almacen",
        store=True
    )

    etapa_recepcion = fields.Selection(
        [
            ("borrador", "Borrador"),
            ("en_cotejo", "En cotejo"),
            ("listo_almacen", "Listo para almacén"),
            ("ingresado", "Ingresado"),
        ],
        string="Etapa",
        compute="_compute_etapa_recepcion",
        store=True
    )

    fecha_envio_almacen = fields.Datetime(
        string="Fecha y hora de envío a almacén",
        readonly=True
    )

    usuario_envio_almacen_id = fields.Many2one(
        "res.users",
        string="Usuario que envió a almacén",
        readonly=True
    )

    total_para_almacen = fields.Float(
        string="Cantidad para almacén",
        compute="_compute_totales_destino",
        store=True
    )

    total_para_estudiante = fields.Float(
        string="Cantidad para estudiante",
        compute="_compute_totales_destino",
        store=True
    )

    @api.depends("matricula_id", "matricula_id.anio_escolar")
    def _compute_datos_matricula(self):
        for rec in self:
            rec.anio = str(rec.matricula_id.anio_escolar or "") if rec.matricula_id else ""

    @api.depends(
        "linea_ids.estado_linea",
        "linea_ids.cantidad_faltante",
        "linea_ids.cantidad_entregada",
    )
    def _compute_resumen(self):
        for rec in self:
            total = len(rec.linea_ids)
            completos = len(rec.linea_ids.filtered(lambda l: l.estado_linea == "completo"))
            faltantes = len(rec.linea_ids.filtered(lambda l: l.cantidad_faltante > 0))

            rec.total_productos = total
            rec.total_completos = completos
            rec.total_faltantes = faltantes
            rec.porcentaje_avance = (completos / total * 100) if total else 0

            if total == 0:
                rec.estado_entrega = "sin_cargar"
            elif faltantes > 0 or completos < total:
                rec.estado_entrega = "incompleto"
            else:
                rec.estado_entrega = "completo"

    @api.depends("total_completos", "total_productos")
    def _compute_items_resumen(self):
        for rec in self:
            rec.items_resumen = f"{rec.total_completos or 0}/{rec.total_productos or 0}"

    @api.depends("total_productos", "total_faltantes", "estado")
    def _compute_estado_visual(self):
        for rec in self:
            if rec.estado == "borrador" or rec.total_productos == 0:
                rec.estado_visual = "pendiente"
            elif rec.total_faltantes > 0:
                rec.estado_visual = "incompleto"
            else:
                rec.estado_visual = "listo"

    @api.depends(
        "linea_ids.destino_recepcion",
        "linea_ids.cantidad_entregada",
        "linea_ids.cantidad_enviada_almacen",
    )
    def _compute_estado_almacen(self):
        for rec in self:
            lineas_almacen = rec.linea_ids.filtered(
                lambda l: l.destino_recepcion == "almacen"
            )

            if not lineas_almacen:
                rec.estado_almacen = "sin_productos"
                continue

            total_entregado_almacen = sum(lineas_almacen.mapped("cantidad_entregada"))
            total_enviado_almacen = sum(lineas_almacen.mapped("cantidad_enviada_almacen"))
            total_pendiente_almacen = sum(lineas_almacen.mapped("cantidad_pendiente_almacen"))

            if total_entregado_almacen <= 0:
                rec.estado_almacen = "pendiente"
            elif total_enviado_almacen <= 0:
                rec.estado_almacen = "pendiente"
            elif total_pendiente_almacen > 0:
                rec.estado_almacen = "parcial"
            else:
                rec.estado_almacen = "enviado"

    @api.depends("estado", "estado_almacen", "total_productos")
    def _compute_etapa_recepcion(self):
        for rec in self:
            if rec.estado == "borrador":
                rec.etapa_recepcion = "borrador"
            elif rec.estado in ["incompleto", "completo"]:
                rec.etapa_recepcion = "en_cotejo"
            elif rec.estado == "validado" and rec.estado_almacen in ["pendiente", "parcial"]:
                rec.etapa_recepcion = "listo_almacen"
            elif rec.estado == "validado" and rec.estado_almacen in ["enviado", "sin_productos"]:
                rec.etapa_recepcion = "ingresado"
            else:
                rec.etapa_recepcion = "en_cotejo"

    @api.depends("linea_ids.cantidad_entregada", "linea_ids.destino_recepcion")
    def _compute_totales_destino(self):
        for rec in self:
            rec.total_para_almacen = sum(
                rec.linea_ids.filtered(
                    lambda l: l.destino_recepcion == "almacen"
                ).mapped("cantidad_entregada")
            )

            rec.total_para_estudiante = sum(
                rec.linea_ids.filtered(
                    lambda l: l.destino_recepcion == "estudiante"
                ).mapped("cantidad_entregada")
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "Nueva") == "Nueva":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "recepcion.utiles.escolar"
                ) or "Nueva"
        return super().create(vals_list)

    def _obtener_valor_linea(self, linea, posibles_campos, valor_default=False):
        for campo in posibles_campos:
            if campo in linea._fields:
                return linea[campo]
        return valor_default

    def _calcular_destino_recepcion(self, tipo_uso):
        texto = (tipo_uso or "").lower().strip()

        if (
            "personal" in texto
            or "util personal" in texto
            or "útil personal" in texto
            or "niño" in texto
            or "niña" in texto
            or "estudiante" in texto
        ):
            return "estudiante"

        return "almacen"

    def action_recalcular_destinos(self):
        for rec in self:
            for linea in rec.linea_ids:
                destino = rec._calcular_destino_recepcion(linea.tipo_uso_escolar)

                valores = {
                    "destino_recepcion": destino
                }

                if destino == "estudiante":
                    valores["cantidad_enviada_almacen"] = 0

                linea.write(valores)

    def action_cargar_lista(self):
        for rec in self:
            if not rec.matricula_id:
                raise UserError("Primero debes seleccionar una matrícula.")

            if not rec.lista_id:
                raise UserError("La matrícula seleccionada no tiene una lista de útiles asociada.")

            if "linea_ids" not in rec.lista_id._fields:
                raise UserError(
                    "No se encontró el campo linea_ids en la lista de útiles. "
                    "Revisa cómo se llama el detalle de productos en tu modelo lista.utiles.grado."
                )

            comandos = [(5, 0, 0)]

            for linea in rec.lista_id.linea_ids:
                producto = rec._obtener_valor_linea(
                    linea,
                    ["product_id", "producto_id"]
                )

                cantidad = rec._obtener_valor_linea(
                    linea,
                    ["cantidad_esperada", "cantidad", "product_qty"],
                    0
                )

                unidad = rec._obtener_valor_linea(
                    linea,
                    ["unidad_id", "uom_id"]
                )

                categoria = rec._obtener_valor_linea(
                    linea,
                    ["categoria_id", "categ_id"]
                )

                tipo_uso = rec._obtener_valor_linea(
                    linea,
                    ["tipo_uso_escolar"],
                    ""
                )

                observacion = rec._obtener_valor_linea(
                    linea,
                    ["observacion", "note"],
                    ""
                )

                if not producto:
                    continue

                if not categoria and producto:
                    categoria = producto.categ_id

                tipo_uso_texto = tipo_uso

                if "tipo_uso_escolar" in linea._fields:
                    field_tipo = linea._fields["tipo_uso_escolar"]
                    if field_tipo.type == "selection":
                        try:
                            seleccion = dict(field_tipo._description_selection(self.env))
                            tipo_uso_texto = seleccion.get(tipo_uso, tipo_uso)
                        except Exception:
                            tipo_uso_texto = tipo_uso

                destino = rec._calcular_destino_recepcion(tipo_uso_texto)

                comandos.append((0, 0, {
                    "product_id": producto.id,
                    "cantidad_esperada": cantidad,
                    "cantidad_entregada": 0,
                    "unidad_id": unidad.id if unidad else False,
                    "categoria_id": categoria.id if categoria else False,
                    "tipo_uso_escolar": tipo_uso_texto,
                    "destino_recepcion": destino,
                    "cantidad_enviada_almacen": 0,
                    "observacion": observacion,
                }))

            rec.write({
                "linea_ids": comandos,
                "estado": "borrador",
                "fecha_envio_almacen": False,
                "usuario_envio_almacen_id": False,
            })

    def action_calcular_faltantes(self):
        for rec in self:
            if not rec.linea_ids:
                raise UserError("Primero debes cargar los productos de la lista.")

            tiene_faltantes = any(linea.cantidad_faltante > 0 for linea in rec.linea_ids)

            rec.estado = "incompleto" if tiene_faltantes else "completo"

    def action_validar(self):
        for rec in self:
            rec.action_calcular_faltantes()
            rec.estado = "validado"

    def action_enviar_productos_almacen(self):
        procesadas = 0
        omitidas = 0
        sin_productos = 0

        for rec in self:
            if rec.estado != "validado":
                omitidas += 1
                continue

            productos_almacen = rec.linea_ids.filtered(
                lambda l: l.destino_recepcion == "almacen"
                and l.cantidad_pendiente_almacen > 0
            )

            if not productos_almacen:
                sin_productos += 1
                continue

            Movimiento = self.env["almacen.utiles.movimiento"]

            for linea in productos_almacen:
                cantidad_a_enviar = linea.cantidad_pendiente_almacen

                valores_movimiento = {
                    "tipo_movimiento": "entrada",
                    "recepcion_id": rec.id,
                    "product_id": linea.product_id.id,
                    "cantidad": cantidad_a_enviar,
                    "unidad_id": linea.unidad_id.id if linea.unidad_id else False,
                    "categoria_id": linea.categoria_id.id if linea.categoria_id else False,
                    "responsable_id": self.env.user.id,
                    "destino": "Almacén general",
                    "observacion": f"Producto enviado a almacén desde la recepción {rec.name}",
                }

                if "recepcion_linea_id" in Movimiento._fields:
                    valores_movimiento["recepcion_linea_id"] = linea.id

                Movimiento.create(valores_movimiento)

                linea.write({
                    "cantidad_enviada_almacen": linea.cantidad_enviada_almacen + cantidad_a_enviar
                })

            rec.write({
                "fecha_envio_almacen": fields.Datetime.now(),
                "usuario_envio_almacen_id": self.env.user.id,
            })

            procesadas += 1

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Envío a almacén",
                "message": f"Recepciones procesadas: {procesadas}. Omitidas: {omitidas}. Sin productos pendientes para almacén: {sin_productos}.",
                "type": "success",
                "sticky": False,
            }
        }

    def action_sincronizar_envios_almacen(self):
        Movimiento = self.env["almacen.utiles.movimiento"]

        for rec in self:
            for linea in rec.linea_ids:
                if linea.destino_recepcion != "almacen":
                    linea.write({
                        "cantidad_enviada_almacen": 0
                    })
                    continue

                movimientos = Movimiento.search([
                    ("recepcion_id", "=", rec.id),
                    ("product_id", "=", linea.product_id.id),
                    ("tipo_movimiento", "=", "entrada"),
                ])

                total_enviado = sum(movimientos.mapped("cantidad"))

                if total_enviado > linea.cantidad_entregada:
                    total_enviado = linea.cantidad_entregada

                linea.write({
                    "cantidad_enviada_almacen": total_enviado
                })

            rec.write({
                "fecha_envio_almacen": fields.Datetime.now(),
                "usuario_envio_almacen_id": self.env.user.id,
            })

    @api.model
    def get_recepciones_almacen_dashboard(self, search=False, estado=False):
        domain = []

        if estado and estado != "todos":
            domain.append(("estado_visual", "=", estado))

        recepciones = self.search(domain, order="fecha desc, id desc")

        if search:
            texto = search.lower().strip()
            recepciones = recepciones.filtered(
                lambda r:
                    texto in (r.estudiante_id.name or "").lower()
                    or texto in (r.recibido_por_id.name or "").lower()
                    or texto in (r._grado_label_dashboard(r.grado_escolar) or "").lower()
                    or texto in (r.name or "").lower()
            )

        rows = []

        for rec in recepciones:
            estado_label = "Pendiente"
            estado_class = "pendiente"

            if rec.estado_visual == "listo":
                estado_label = "Listo"
                estado_class = "listo"
            elif rec.estado_visual == "incompleto":
                estado_label = "Incompleto"
                estado_class = "incompleto"

            rows.append({
                "id": rec.id,
                "alumno": rec.estudiante_id.name or "",
                "iniciales": rec._iniciales_dashboard(rec.estudiante_id.name),
                "grado": rec._grado_label_dashboard(rec.grado_escolar),
                "fecha": rec.fecha.strftime("%d/%m/%Y") if rec.fecha else "",
                "recibido_por": rec.recibido_por_id.name or "",
                "items": rec.items_resumen or "0/0",
                "estado": estado_label,
                "estado_class": estado_class,
            })

        return {
            "total": len(rows),
            "rows": rows,
        }

    @api.model
    def get_recepcion_almacen_detalle(self, recepcion_id):
        rec = self.browse(int(recepcion_id)).exists()

        if not rec:
            return {}

        lineas = []

        for linea in rec.linea_ids:
            estado_label = "Pendiente"
            estado_class = "pendiente"

            if linea.estado_linea == "completo":
                estado_label = "Ok"
                estado_class = "ok"
            elif linea.estado_linea == "faltante":
                estado_label = "Falta"
                estado_class = "falta"

            lineas.append({
                "id": linea.id,
                "producto": linea.product_id.display_name or "",
                "cantidad_requerida": rec._fmt_qty_dashboard(linea.cantidad_esperada),
                "cantidad_recibida": rec._fmt_qty_dashboard(linea.cantidad_entregada),
                "estado": estado_label,
                "estado_class": estado_class,
                "completo": linea.estado_linea == "completo",
            })

        return {
            "id": rec.id,
            "name": rec.name,
            "alumno": rec.estudiante_id.name or "",
            "grado": rec._grado_label_dashboard(rec.grado_escolar),
            "fecha_label": rec.fecha.strftime("%d/%m/%Y") if rec.fecha else "",
            "recibido_por": rec.recibido_por_id.name or "",
            "estado": rec.estado,
            "estado_almacen": rec.estado_almacen,
            "etapa": rec.etapa_recepcion,
            "puede_enviar_almacen": rec.estado == "validado" and rec.estado_almacen in ["pendiente", "parcial"],
            "lineas": lineas,
            "totales": {
                "items": rec.total_productos,
                "recibidos": rec.total_completos,
                "faltantes": rec.total_faltantes,
                "porcentaje": f"{rec._fmt_qty_dashboard(rec.porcentaje_avance)}%",
            }
        }

    @api.model
    def guardar_recepcion_almacen_dashboard(self, recepcion_id, lineas):
        rec = self.browse(int(recepcion_id)).exists()

        if not rec:
            return False

        Linea = self.env["recepcion.utiles.linea"]

        for item in lineas:
            linea = Linea.browse(int(item.get("id"))).exists()
            if linea and linea.recepcion_id.id == rec.id:
                cantidad = item.get("cantidad_recibida") or 0
                linea.write({
                    "cantidad_entregada": float(str(cantidad).replace(",", "."))
                })

        rec.action_calcular_faltantes()

        return True

    @api.model
    def validar_recepcion_almacen_dashboard(self, recepcion_id, lineas):
        self.guardar_recepcion_almacen_dashboard(recepcion_id, lineas)

        rec = self.browse(int(recepcion_id)).exists()
        if rec:
            rec.action_validar()

        return True

    @api.model
    def borrar_recepciones_dashboard(self, recepcion_ids):
        recepcion_ids = [int(item) for item in recepcion_ids or []]
        recepciones = self.browse(recepcion_ids).exists()

        if not recepciones:
            return {"deleted": 0}

        bloqueadas = recepciones.filtered(
            lambda rec: rec.estado == "validado" or rec.movimiento_almacen_ids
        )

        if bloqueadas:
            nombres = ", ".join(bloqueadas.mapped("name"))
            raise UserError(
                "No se pueden borrar recepciones validadas o con movimientos de almacén: %s" % nombres
            )

        total = len(recepciones)
        recepciones.unlink()

        return {"deleted": total}
    
    @api.model
    def enviar_recepcion_almacen_dashboard(self, recepcion_id):
        rec = self.browse(int(recepcion_id)).exists()

        if not rec:
            raise UserError("No se encontró la recepción.")

        if rec.estado != "validado":
            raise UserError("Primero debes validar la recepción antes de enviarla al almacén.")

        productos_almacen = rec.linea_ids.filtered(
            lambda l: l.destino_recepcion == "almacen"
            and l.cantidad_pendiente_almacen > 0
        )

        if not productos_almacen:
            return {
                "success": False,
                "message": "No hay productos pendientes para almacén. Los útiles personales no se envían al almacén.",
            }

        rec.action_enviar_productos_almacen()

        return {
            "success": True,
            "message": "Productos enviados al almacén correctamente.",
        }

    @api.model
    def enviar_recepcion_almacen_dashboard(self, recepcion_id):
        rec = self.browse(int(recepcion_id)).exists()

        if not rec:
            raise UserError("No se encontró la recepción.")

        if rec.estado != "validado":
            raise UserError("Primero debes validar la recepción antes de enviarla al almacén.")

        productos_almacen = rec.linea_ids.filtered(
            lambda l: l.destino_recepcion == "almacen"
            and l.cantidad_pendiente_almacen > 0
        )

        if not productos_almacen:
            return {
                "success": False,
                "message": "No hay productos pendientes para almacén. Los útiles personales no se envían al almacén.",
            }

        rec.action_enviar_productos_almacen()

        return {
            "success": True,
            "message": "Productos enviados al almacén correctamente.",
        }

class RecepcionUtilesLinea(models.Model):
    _name = "recepcion.utiles.linea"
    _description = "Detalle de recepción de útiles escolares"

    recepcion_id = fields.Many2one(
        "recepcion.utiles.escolar",
        string="Recepción",
        required=True,
        ondelete="cascade"
    )

    product_id = fields.Many2one(
        "product.product",
        string="Producto",
        required=True
    )

    categoria_id = fields.Many2one(
        "product.category",
        string="Categoría",
        readonly=True
    )

    cantidad_esperada = fields.Float(
        string="Cantidad esperada",
        required=True
    )

    cantidad_entregada = fields.Float(
        string="Cantidad entregada",
        default=0
    )

    cantidad_faltante = fields.Float(
        string="Cantidad faltante",
        compute="_compute_cantidad_faltante",
        store=True
    )

    unidad_id = fields.Many2one(
        "uom.uom",
        string="Unidad"
    )

    tipo_uso_escolar = fields.Char(
        string="Tipo de uso escolar"
    )

    destino_recepcion = fields.Selection(
        [
            ("estudiante", "Se queda con estudiante"),
            ("almacen", "Enviar a almacén"),
        ],
        string="Destino",
        default="almacen"
    )

    cantidad_enviada_almacen = fields.Float(
        string="Cantidad enviada a almacén",
        default=0,
        readonly=True
    )

    cantidad_pendiente_almacen = fields.Float(
        string="Pendiente de enviar a almacén",
        compute="_compute_cantidad_pendiente_almacen",
        store=True
    )

    estado_envio_almacen = fields.Selection(
        [
            ("no_aplica", "No aplica"),
            ("pendiente", "Pendiente"),
            ("parcial", "Parcial"),
            ("enviado", "Enviado"),
        ],
        string="Estado almacén",
        compute="_compute_cantidad_pendiente_almacen",
        store=True
    )

    estado_linea = fields.Selection(
        [
            ("pendiente", "Pendiente"),
            ("faltante", "Faltante"),
            ("completo", "Completo"),
        ],
        string="Estado",
        compute="_compute_cantidad_faltante",
        store=True
    )

    observacion = fields.Char(string="Observación")

    @api.depends("cantidad_esperada", "cantidad_entregada")
    def _compute_cantidad_faltante(self):
        for linea in self:
            faltante = linea.cantidad_esperada - linea.cantidad_entregada

            linea.cantidad_faltante = faltante if faltante > 0 else 0

            if linea.cantidad_entregada <= 0:
                linea.estado_linea = "pendiente"
            elif linea.cantidad_faltante > 0:
                linea.estado_linea = "faltante"
            else:
                linea.estado_linea = "completo"

    @api.depends("destino_recepcion", "cantidad_entregada", "cantidad_enviada_almacen")
    def _compute_cantidad_pendiente_almacen(self):
        for rec in self:
            if rec.destino_recepcion != "almacen":
                rec.cantidad_pendiente_almacen = 0
                rec.estado_envio_almacen = "no_aplica"
            else:
                pendiente = rec.cantidad_entregada - rec.cantidad_enviada_almacen
                rec.cantidad_pendiente_almacen = pendiente if pendiente > 0 else 0

                if rec.cantidad_entregada <= 0:
                    rec.estado_envio_almacen = "pendiente"
                elif rec.cantidad_enviada_almacen <= 0:
                    rec.estado_envio_almacen = "pendiente"
                elif rec.cantidad_enviada_almacen < rec.cantidad_entregada:
                    rec.estado_envio_almacen = "parcial"
                else:
                    rec.estado_envio_almacen = "enviado"

    @api.onchange("tipo_uso_escolar")
    def _onchange_tipo_uso_escolar_destino(self):
        for rec in self:
            texto = (rec.tipo_uso_escolar or "").lower()

            if (
                "personal" in texto
                or "util personal" in texto
                or "útil personal" in texto
                or "niño" in texto
                or "niña" in texto
                or "estudiante" in texto
            ):
                rec.destino_recepcion = "estudiante"
            else:
                rec.destino_recepcion = "almacen"
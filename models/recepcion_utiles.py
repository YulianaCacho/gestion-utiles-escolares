from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError


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

    tipo_entrada = fields.Selection(
    [
        ("recepcion_utiles", "Recepción de útiles escolares"),
        ("compra_directa", "Compra directa"),
        ("traslado_interno", "Traslado interno"),
        ("otro", "Otro"),
    ],
    string="Tipo de entrada",
    default="recepcion_utiles",
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
        string="Registrado por",
        default=lambda self: self.env.user,
        readonly=True
    )

    comprado_por_id = fields.Many2one(
        "res.partner",
        string="Comprado por",
        domain=[
            (
                "tipo_contacto_escolar",
                "=",
                "personal"
            ),
            (
                "cargo_institucional",
                "in",
                [
                    "directora",
                    "coordinadora",
                    "promotora",
                    "secretaria",
                ]
            ),
        ],
        ondelete="restrict"
    )

    grado_origen_traslado = fields.Selection(
        [
            ("inicial_3", "Inicial 3 años"),
            ("inicial_4", "Inicial 4 años"),
            ("inicial_5", "Inicial 5 años"),
            ("1er_grado", "1er grado"),
            ("2do_grado", "2do grado"),
            ("3er_grado", "3er grado"),
            ("4to_grado", "4to grado"),
            ("5to_grado", "5to grado"),
            ("6to_grado", "6to grado"),
        ],
        string="Grado que entrega"
    )

    grado_destino_traslado = fields.Selection(
        [
            ("inicial_3", "Inicial 3 años"),
            ("inicial_4", "Inicial 4 años"),
            ("inicial_5", "Inicial 5 años"),
            ("1er_grado", "1er grado"),
            ("2do_grado", "2do grado"),
            ("3er_grado", "3er grado"),
            ("4to_grado", "4to grado"),
            ("5to_grado", "5to grado"),
            ("6to_grado", "6to grado"),
        ],
        string="Grado que recibe"
    )

    encargado_entrega_id = fields.Many2one(
        "res.partner",
        string="Persona encargada de la entrega",
        domain=[
            (
                "tipo_contacto_escolar",
                "=",
                "personal"
            )
        ],
        ondelete="restrict"
    )

    traslado_ejecutado = fields.Boolean(
        string="Traslado realizado",
        default=False,
        readonly=True,
        copy=False
    )

    fecha_traslado = fields.Datetime(
        string="Fecha del traslado",
        readonly=True,
        copy=False
    )

    usuario_traslado_id = fields.Many2one(
        "res.users",
        string="Usuario que realizó el traslado",
        readonly=True,
        copy=False
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

    @api.constrains("matricula_id")
    def _check_matricula_anio_seleccionado(self):
        for rec in self:

            if not rec.matricula_id:
                continue

            anio_seleccionado = (
                self.env.user.anio_escolar_actual_id
            )

            anio_matricula = (
                rec.matricula_id.anio_escolar_id
            )

            if (
                anio_seleccionado
                and anio_matricula
                and anio_matricula != anio_seleccionado
            ):
                raise ValidationError(
                    "No se puede guardar la recepción.\n\n"
                    f"La matrícula seleccionada pertenece al año "
                    f"{anio_matricula.anio}, pero actualmente está "
                    f"seleccionado el año escolar "
                    f"{anio_seleccionado.anio}.\n\n"
                    "Seleccione una matrícula correspondiente "
                    "al año escolar seleccionado."
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

    def _estado_matricula_label(self, matricula):
        selection = dict(matricula._fields["estado"].selection)
        return selection.get(matricula.estado, matricula.estado or "Sin estado")

    def _ensure_matricula_activa_para_recepcion(self):
        for rec in self:
            if rec.tipo_entrada != "recepcion_utiles":
                continue

            if not rec.matricula_id:
                continue

            if rec.matricula_id.estado != "activo":
                estado = rec._estado_matricula_label(rec.matricula_id)
                estudiante = rec.matricula_id.estudiante_id.name or "el estudiante"

                raise UserError(
                    "No se puede registrar recepción de útiles para %s porque su matrícula está en estado '%s'. "
                    "Solo las matrículas en estado 'Activo' pueden registrar recepción de útiles."
                    % (estudiante, estado)
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "Nueva") == "Nueva":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "recepcion.utiles.escolar"
                ) or "Nueva"

            tipo_entrada = vals.get("tipo_entrada", "recepcion_utiles")
            matricula_id = vals.get("matricula_id")

            if tipo_entrada == "recepcion_utiles" and matricula_id:
                matricula = self.env["matricula.escolar"].browse(
                    matricula_id
                )

                if matricula.estado != "activo":
                    estado = dict(
                        matricula._fields["estado"].selection
                    ).get(
                        matricula.estado,
                        matricula.estado or "Sin estado"
                    )

                    raise UserError(
                        "No se puede registrar recepción de útiles "
                        "para %s porque su matrícula está en estado '%s'. "
                        "Solo las matrículas en estado 'Activo' "
                        "pueden registrar recepción de útiles."
                        % (
                            matricula.estudiante_id.name
                            or "el estudiante",
                            estado
                        )
                    )

        records = super().create(vals_list)
        records._ensure_matricula_activa_para_recepcion()
        return records

    @api.constrains("matricula_id", "tipo_entrada")
    def _check_recepcion_unica_por_matricula(self):
        for rec in self:
            if rec.tipo_entrada != "recepcion_utiles":
                continue
            if not rec.matricula_id:
                continue
            existe = self.search_count([
                ("matricula_id", "=", rec.matricula_id.id),
                ("tipo_entrada", "=", "recepcion_utiles"),
                ("id", "!=", rec.id),
            ])
            if existe:
                raise UserError(
                    f"El alumno {rec.matricula_id.estudiante_id.name} ya tiene una recepción registrada."
                )

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

    def _obtener_lista_correcta_por_matricula(self):
        """Obtiene la lista del mismo año y grado de la matrícula."""

        self.ensure_one()

        matricula = self.matricula_id

        if not matricula or not matricula.grado_escolar:
            return self.env["lista.utiles.grado"]

        dominio = [
            ("grado_escolar", "=", matricula.grado_escolar),
        ]

        if (
            "anio_escolar_id" in self.env["lista.utiles.grado"]._fields
            and matricula.anio_escolar_id
        ):
            dominio.append(
                ("anio_escolar_id", "=", matricula.anio_escolar_id.id)
            )

        lista = self.env["lista.utiles.grado"].search(
            dominio,
            order="id desc",
            limit=1,
        )

        if not lista and matricula.anio_escolar_id:
            lista = self.env["lista.utiles.grado"].search(
                [
                    ("grado_escolar", "=", matricula.grado_escolar),
                    ("anio", "=", str(matricula.anio_escolar_id.anio)),
                ],
                order="id desc",
                limit=1,
            )

        return lista

    @api.onchange("matricula_id")
    def _onchange_matricula_id_cargar_lista(self):
        for rec in self:
            if rec.tipo_entrada != "recepcion_utiles":
                continue

            if rec.matricula_id and rec.matricula_id.estado != "activo":
                estado = rec._estado_matricula_label(rec.matricula_id)
                estudiante = rec.matricula_id.estudiante_id.name or "el estudiante"

                rec.matricula_id = False
                rec.linea_ids = [(5, 0, 0)]

                return {
                    "warning": {
                        "title": "Matrícula no activa",
                        "message": (
                            "No se puede registrar recepción de útiles para %s porque su matrícula está en estado '%s'. "
                            "Solo se permite recepción cuando la matrícula está Activa."
                            % (estudiante, estado)
                        ),
                }
            }

            if rec.matricula_id:
                existe = self.env["recepcion.utiles.escolar"].search_count([
                    ("matricula_id", "=", rec.matricula_id.id),
                    ("tipo_entrada", "=", "recepcion_utiles"),
                    ("id", "!=", rec._origin.id or 0),
                ])
                if existe:
                    rec.matricula_id = False
                    return {
                        "warning": {
                            "title": "Alumno ya registrado",
                            "message": "Este alumno ya tiene una recepción registrada. Selecciona otro alumno.",
                        }
                    }

            rec.linea_ids = [(5, 0, 0)]
            rec.estado = "borrador"
            rec.fecha_envio_almacen = False
            rec.usuario_envio_almacen_id = False

            if not rec.matricula_id:
                continue

            lista_correcta = rec._obtener_lista_correcta_por_matricula()

            if not lista_correcta:
                return {
                    "warning": {
                        "title": "Lista no encontrada",
                        "message": (
                            "No se encontró una lista de útiles para "
                            "el mismo año y grado de la matrícula seleccionada."
                        ),
                    }
                }

            comandos = [(5, 0, 0)]

            for linea in lista_correcta.linea_ids:
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

                producto_recepcion = producto.product_variant_id if producto._name == "product.template" else producto

                if not producto_recepcion:
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
                    "product_id": producto_recepcion.id,
                    "cantidad_esperada": cantidad,
                    "cantidad_entregada": 0,
                    "unidad_id": unidad.id if unidad else False,
                    "categoria_id": categoria.id if categoria else False,
                    "tipo_uso_escolar": tipo_uso_texto,
                    "destino_recepcion": destino,
                    "cantidad_enviada_almacen": 0,
                    "observacion": observacion,
                }))

            rec.linea_ids = comandos

    def action_cargar_lista(self):
        for rec in self:
            if not rec.matricula_id:
                raise UserError("Primero debes seleccionar una matrícula.")
            rec._ensure_matricula_activa_para_recepcion()

            lista_correcta = rec._obtener_lista_correcta_por_matricula()

            if not lista_correcta:
                raise UserError(
                    "No se encontró una lista de útiles para el mismo año y "
                    "grado de la matrícula seleccionada."
                )

            if "linea_ids" not in lista_correcta._fields:
                raise UserError(
                    "No se encontró el campo linea_ids en la lista de útiles. "
                    "Revisa cómo se llama el detalle de productos en tu modelo lista.utiles.grado."
                )

            if rec.matricula_id.lista_utiles_id != lista_correcta:
                rec.matricula_id.with_context(
                    skip_anio_check=True
                ).write({
                    "lista_utiles_id": lista_correcta.id,
                })

            comandos = [(5, 0, 0)]

            for linea in lista_correcta.linea_ids:
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

                producto_recepcion = producto.product_variant_id if producto._name == "product.template" else producto

                if not producto_recepcion:
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
                    "product_id": producto_recepcion.id,
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
        self._ensure_matricula_activa_para_recepcion()
        for rec in self:
            if not rec.linea_ids:
                raise UserError("Primero debes cargar los productos de la lista.")

            tiene_faltantes = any(linea.cantidad_faltante > 0 for linea in rec.linea_ids)

            rec.estado = "incompleto" if tiene_faltantes else "completo"

    def _validar_cantidades_recepcion(self):
        """
        Verifica todas las cantidades antes de guardar
        o validar una recepción.
        """

        errores = []

        for rec in self:

            for linea in rec.linea_ids:

                producto = (
                    linea.product_id.display_name
                    or "Producto sin nombre"
                )

                cantidad = float(
                    linea.cantidad_entregada or 0
                )

                cantidad_maxima = float(
                    linea.cantidad_esperada or 0
                )

                # No permitir cantidades negativas
                if cantidad < 0:

                    errores.append(
                        f"{producto}: se ingresó "
                        f"{cantidad:g}, pero no se permiten "
                        f"cantidades negativas."
                    )

                # No permitir números decimales
                elif not cantidad.is_integer():

                    errores.append(
                        f"{producto}: se ingresó "
                        f"{cantidad:g}, pero solo se permiten "
                        f"números enteros."
                    )

                # No permitir superar lo solicitado
                elif cantidad > cantidad_maxima:

                    errores.append(
                        f"{producto}: se ingresó "
                        f"{cantidad:g}, pero la cantidad "
                        f"requerida es {cantidad_maxima:g}."
                    )

        if errores:

            detalle = "\n".join(
                f"• {error}"
                for error in errores
            )

            raise ValidationError(
                "No se puede continuar porque existen "
                "cantidades incorrectas:\n\n"
                f"{detalle}\n\n"
                "Las cantidades deben ser números enteros, "
                "mayores o iguales a cero y no deben superar "
                "la cantidad requerida."
            )

        return True

    def action_guardar_recepcion_form(self):
        """
        Guarda y verifica las cantidades
        ingresadas desde el formulario.
        """

        self.ensure_one()

        self._validar_cantidades_recepcion()

        self.action_calcular_faltantes()

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Recepción guardada",
                "message": (
                    "Los cambios se guardaron "
                    "correctamente."
                ),
                "type": "success",
                "sticky": False,
            }
        }


    def action_volver_dashboard_recepcion(self):
        """
        Regresa al dashboard principal
        de recepciones.
        """

        return (
            self.env[
                "ir.actions.actions"
            ]._for_xml_id(
                "gestion_utiles_escolares."
                "action_recepcion_utiles_almacen_dashboard"
            )
        )

    @api.constrains(
        "tipo_entrada",
        "comprado_por_id"
    )
    def _check_comprado_por(self):

        cargos_permitidos = {
            "directora",
            "coordinadora",
            "promotora",
            "secretaria",
        }

        for rec in self:

            if rec.tipo_entrada != "compra_directa":
                continue

            if not rec.comprado_por_id:
                raise ValidationError(
                    "Debe seleccionar a la persona "
                    "que realizó la compra."
                )

            if (
                rec.comprado_por_id.tipo_contacto_escolar
                != "personal"
                or
                rec.comprado_por_id.cargo_institucional
                not in cargos_permitidos
            ):
                raise ValidationError(
                    "La persona seleccionada en "
                    "'Comprado por' debe tener uno "
                    "de los siguientes cargos:\n\n"
                    "• Directora\n"
                    "• Coordinadora\n"
                    "• Promotora\n"
                    "• Secretaria"
                )

    def _validar_compra_directa(self):

        for rec in self:

            errores = []

            if not rec.comprado_por_id:
                errores.append(
                    "No se seleccionó a la persona "
                    "que realizó la compra."
                )

            if not rec.linea_ids:
                errores.append(
                    "No se agregó ningún producto."
                )

            for linea in rec.linea_ids:

                producto = (
                    linea.product_id.display_name
                    or "Producto sin nombre"
                )

                cantidad = float(
                    linea.cantidad_entregada or 0
                )

                if not linea.unidad_id:

                    errores.append(
                        f"{producto}: seleccione "
                        f"una unidad."
                    )

                if cantidad < 0:

                    errores.append(
                        f"{producto}: la cantidad "
                        f"{cantidad:g} es negativa."
                    )

                elif not cantidad.is_integer():

                    errores.append(
                        f"{producto}: la cantidad "
                        f"{cantidad:g} contiene "
                        f"decimales. Solo se permiten "
                        f"números enteros."
                    )

            if errores:

                detalle = "\n".join(
                    f"• {error}"
                    for error in errores
                )

                raise ValidationError(
                    "No se puede validar la compra "
                    "porque existen inconsistencias:"
                    "\n\n"
                    f"{detalle}"
                    "\n\n"
                    "Corrija los datos indicados "
                    "y vuelva a validar."
                )

        return True

    def _stock_disponible_para_traslado(
        self,
        producto
    ):

        self.ensure_one()

        if (
            not producto
            or
            not self.grado_origen_traslado
        ):
            return 0.0

        dominio = [
            (
                "product_id",
                "=",
                producto.id
            ),
            (
                "grado_escolar",
                "=",
                self.grado_origen_traslado
            ),
        ]

        if self.anio_escolar_id:

            dominio.append(
                (
                    "anio_escolar_id",
                    "=",
                    self.anio_escolar_id.id
                )
            )

        movimientos = self.env[
            "almacen.utiles.movimiento"
        ].search(
            dominio
        )

        entradas = sum(
            movimientos.filtered(
                lambda movimiento:
                    movimiento.tipo_movimiento
                    == "entrada"
            ).mapped(
                "cantidad"
            )
        )

        salidas = sum(
            movimientos.filtered(
                lambda movimiento:
                    movimiento.tipo_movimiento
                    == "salida"
            ).mapped(
                "cantidad"
            )
        )

        return entradas - salidas

    def _validar_traslado_interno(self):

        for rec in self:

            errores = []

            if not rec.grado_origen_traslado:

                errores.append(
                    "Debe seleccionar el grado "
                    "que entrega los útiles."
                )

            if not rec.grado_destino_traslado:

                errores.append(
                    "Debe seleccionar el grado "
                    "que recibe los útiles."
                )

            if (
                rec.grado_origen_traslado
                and
                rec.grado_destino_traslado
                and
                rec.grado_origen_traslado
                ==
                rec.grado_destino_traslado
            ):

                errores.append(
                    "El grado que entrega y el "
                    "grado que recibe no pueden "
                    "ser el mismo."
                )

            if not rec.encargado_entrega_id:

                errores.append(
                    "Debe seleccionar a la persona "
                    "encargada de la entrega."
                )

            if not rec.linea_ids:

                errores.append(
                    "Debe agregar al menos un "
                    "producto al traslado."
                )

            cantidades_por_producto = {}

            for linea in rec.linea_ids:

                producto = linea.product_id

                if not producto:

                    errores.append(
                        "Existe una línea sin "
                        "producto seleccionado."
                    )

                    continue

                cantidad = float(
                    linea.cantidad_entregada
                    or 0
                )

                nombre = (
                    producto.display_name
                    or
                    "Producto sin nombre"
                )

                if cantidad <= 0:

                    errores.append(
                        f"{nombre}: la cantidad "
                        f"saliente debe ser mayor "
                        f"a cero."
                    )

                elif not cantidad.is_integer():

                    errores.append(
                        f"{nombre}: la cantidad "
                        f"{cantidad:g} contiene "
                        f"decimales. Solo se "
                        f"permiten números enteros."
                    )

                cantidades_por_producto[
                    producto.id
                ] = (
                    cantidades_por_producto.get(
                        producto.id,
                        0
                    )
                    +
                    cantidad
                )

            for (
                producto_id,
                cantidad_total
            ) in cantidades_por_producto.items():

                producto = self.env[
                    "product.product"
                ].browse(
                    producto_id
                )

                stock = (
                    rec
                    ._stock_disponible_para_traslado(
                        producto
                    )
                )

                nombre = (
                    producto.display_name
                    or
                    "Producto sin nombre"
                )

                if stock <= 0:

                    errores.append(
                        f"{nombre}: el producto "
                        f"no tiene stock disponible "
                        f"en el grado que entrega."
                    )

                elif cantidad_total > stock:

                    errores.append(
                        f"{nombre}: se solicitó "
                        f"trasladar "
                        f"{cantidad_total:g}, "
                        f"pero el stock disponible "
                        f"es {stock:g}."
                    )

            if errores:

                detalle = "\n".join(
                    f"• {error}"
                    for error in errores
                )

                raise ValidationError(
                    "No se puede validar el "
                    "traslado porque existen "
                    "inconsistencias:"
                    "\n\n"
                    f"{detalle}"
                    "\n\n"
                    "Corrija los datos indicados "
                    "y vuelva a validar."
                )

        return True

    def action_validar(self):

        for rec in self:

            # Traslado interno
            if (
                rec.tipo_entrada
                == "traslado_interno"
            ):

                rec._validar_traslado_interno()

                rec.estado = "validado"

                continue

            # Compra directa
            if (
                rec.tipo_entrada
                == "compra_directa"
            ):

                rec._validar_compra_directa()

                rec.estado = "validado"

                continue

            # Recepción por matrícula
            rec._ensure_matricula_activa_para_recepcion()

            rec._validar_cantidades_recepcion()

            rec.action_calcular_faltantes()

            rec.estado = "validado"

    def action_ejecutar_traslado_interno(self):

        Movimiento = self.env[
            "almacen.utiles.movimiento"
        ]

        grados = dict(
            self.env[
                "matricula.escolar"
            ]._fields[
                "grado_escolar"
            ].selection
        )

        for rec in self:

            if (
                rec.tipo_entrada
                != "traslado_interno"
            ):

                raise UserError(
                    "Esta operación solo está "
                    "disponible para traslados "
                    "internos."
                )

            if rec.estado != "validado":

                raise UserError(
                    "Primero debe validar el "
                    "traslado."
                )

            if rec.traslado_ejecutado:

                raise UserError(
                    "Este traslado ya fue "
                    "realizado."
                )

            rec._validar_traslado_interno()

            grado_origen_texto = grados.get(
                rec.grado_origen_traslado,
                rec.grado_origen_traslado
            )

            grado_destino_texto = grados.get(
                rec.grado_destino_traslado,
                rec.grado_destino_traslado
            )

            for linea in rec.linea_ids:

                cantidad = (
                    linea.cantidad_entregada
                )

                valores_comunes = {

                    "anio_escolar_id":
                        rec.anio_escolar_id.id
                        if rec.anio_escolar_id
                        else False,

                    "recepcion_id":
                        rec.id,

                    "product_id":
                        linea.product_id.id,

                    "cantidad":
                        cantidad,

                    "unidad_id":
                        linea.unidad_id.id
                        if linea.unidad_id
                        else False,

                    "categoria_id":
                        linea.categoria_id.id
                        if linea.categoria_id
                        else False,

                    "responsable_id":
                        self.env.user.id,
                }

                valores_salida = {
                    **valores_comunes,

                    "tipo_movimiento":
                        "salida",

                    "grado_escolar":
                        rec.grado_origen_traslado,

                    "destino":
                        (
                            "Traslado interno hacia "
                            f"{grado_destino_texto}"
                        ),

                    "observacion":
                        (
                            f"Salida por traslado "
                            f"interno {rec.name}. "
                            f"Entrega: "
                            f"{rec.encargado_entrega_id.name}. "
                            f"Origen: "
                            f"{grado_origen_texto}. "
                            f"Destino: "
                            f"{grado_destino_texto}."
                        ),
                }

                Movimiento.create(
                    valores_salida
                )

                valores_entrada = {
                    **valores_comunes,

                    "tipo_movimiento":
                        "entrada",

                    "grado_escolar":
                        rec.grado_destino_traslado,

                    "destino":
                        grado_destino_texto,

                    "observacion":
                        (
                            f"Entrada por traslado "
                            f"interno {rec.name}. "
                            f"Origen: "
                            f"{grado_origen_texto}. "
                            f"Destino: "
                            f"{grado_destino_texto}."
                        ),
                }

                Movimiento.create(
                    valores_entrada
                )

            rec.write({

                "traslado_ejecutado":
                    True,

                "fecha_traslado":
                    fields.Datetime.now(),

                "usuario_traslado_id":
                    self.env.user.id,
            })

        return {
            "type":
                "ir.actions.client",

            "tag":
                "display_notification",

            "params": {

                "title":
                    "Traslado realizado",

                "message":
                    (
                        "Los productos fueron "
                        "trasladados correctamente."
                    ),

                "type":
                    "success",

                "sticky":
                    False,
            }
        }

    def action_enviar_productos_almacen(self):
        self._ensure_matricula_activa_para_recepcion()

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
                    "anio_escolar_id":
                        rec.anio_escolar_id.id
                        if rec.anio_escolar_id
                        else False,
                    "grado_escolar":
                        rec.grado_escolar
                        if
                        rec.tipo_entrada
                        == "recepcion_utiles"
                        else False,
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

        anio_seleccionado = self.env.user.anio_escolar_actual_id

        if anio_seleccionado:
            domain.append(
                ("anio_escolar_id", "=", anio_seleccionado.id)
            )

        if estado and estado != "todos":
            domain.append(
                ("estado_visual", "=", estado)
            )
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

            tipo_entrada_labels = {
                "recepcion_utiles": "Recepción de útiles",
                "compra_directa": "Compra directa",
                "traslado_interno": "Traslado interno",
                "sobrante_anio_anterior": "Útiles sobrantes del año anterior",
                "otro": "Otro ingreso",
            }

            if rec.estudiante_id:
                alumno = rec.estudiante_id.name
                iniciales = rec._iniciales_dashboard(rec.estudiante_id.name)
                grado = rec._grado_label_dashboard(rec.grado_escolar)
            else:
                alumno = tipo_entrada_labels.get(rec.tipo_entrada, "Ingreso externo")
                iniciales = (
                    "SA"
                    if rec.tipo_entrada == "sobrante_anio_anterior"
                    else rec.tipo_entrada[0].upper()
                    if rec.tipo_entrada
                    else "?"
                )
                grado = (
                    rec._grado_label_dashboard(rec.grado_entrada_sobrante)
                    if (
                        rec.tipo_entrada == "sobrante_anio_anterior"
                        and "grado_entrada_sobrante" in rec._fields
                    )
                    else ""
                )

            rows.append({
                "id": rec.id,
                "alumno": alumno,
                "iniciales": iniciales,
                "grado": grado,
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
                "cantidad_maxima": float(
                        linea.cantidad_esperada or 0
                ),
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
    def guardar_recepcion_almacen_dashboard(
        self,
        recepcion_id,
        lineas
    ):
        rec = self.browse(
            int(recepcion_id)
        ).exists()

        if not rec:
            raise UserError(
            "No se encontró la recepción que desea guardar."
            )

        Linea = self.env[
            "recepcion.utiles.linea"
        ]

        valores_validos = []
        errores = []

        for item in lineas or []:

            linea_id = item.get("id")

            if not linea_id:
                continue

            linea = Linea.browse(
                int(linea_id)
            ).exists()

            if (
                not linea
                or linea.recepcion_id.id != rec.id
            ):
                continue

            producto = (
                linea.product_id.display_name
                or "Producto sin nombre"
            )

            valor_original = item.get(
                "cantidad_recibida"
            )

            # Un campo vacío será considerado cero
            if valor_original in (
                None,
                "",
                False
            ):
                cantidad = 0.0

            else:

                try:

                    cantidad = float(
                        str(
                            valor_original
                        ).replace(",", ".")
                    )

                except (
                    TypeError,
                    ValueError
                ):

                    errores.append(
                        f"{producto}: la cantidad "
                        f"'{valor_original}' no es "
                        f"un número válido."
                    )

                    continue

            cantidad_requerida = float(
                linea.cantidad_esperada or 0
            )

            # No permitir números negativos
            if cantidad < 0:

                errores.append(
                    f"{producto}: se ingresó "
                    f"{rec._fmt_qty_dashboard(cantidad)}, "
                    f"pero no se permiten "
                    f"cantidades negativas."
                )

                continue

            # No permitir cantidades decimales
            if not cantidad.is_integer():

                errores.append(
                    f"{producto}: se ingresó "
                    f"{cantidad:g}, pero solo se permiten "
                    f"números enteros."
                )

            continue

            # No permitir una cantidad mayor
            # a la solicitada en la lista
            if cantidad > cantidad_requerida:

                errores.append(
                    f"{producto}: se ingresó "
                    f"{rec._fmt_qty_dashboard(cantidad)}, "
                    f"pero la cantidad requerida es "
                    f"{rec._fmt_qty_dashboard(cantidad_requerida)}."
                )

                continue

            valores_validos.append(
                (
                    linea,
                    cantidad
                )
            )

        # Mostrar todos los productos con error
        # antes de guardar cualquier cantidad
        if errores:

            detalle_errores = "\n".join(
                f"• {error}"
                for error in errores
            )

            raise UserError(
                "No se puede guardar la recepción "
                "porque se encontraron cantidades "
                "incorrectas:\n\n"
                f"{detalle_errores}\n\n"
                "Corrige únicamente los productos "
                "indicados y vuelve a guardar."
            )

        # Solo guardar cuando todas
        # las cantidades sean válidas
        for linea, cantidad in valores_validos:

            linea.write({
                "cantidad_entregada":
                    cantidad
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
        required=False,
        default=0.0,
        digits=(16, 0),
    )

    cantidad_entregada = fields.Float(
        string="Cantidad entregada",
        default=0
    )

    stock_disponible_traslado = fields.Float(
        string="Stock disponible",
        compute=(
            "_compute_stock_disponible_traslado"
        ),
        digits=(16, 0)
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

    @api.depends(
        "product_id",
        "recepcion_id.grado_origen_traslado",
        "recepcion_id.anio_escolar_id"
    )
    def _compute_stock_disponible_traslado(
        self
    ):

        for linea in self:

            if (
                not linea.product_id
                or
                not linea.recepcion_id
                or
                linea.recepcion_id.tipo_entrada
                != "traslado_interno"
            ):

                linea.stock_disponible_traslado = 0

                continue

            linea.stock_disponible_traslado = (
                linea.recepcion_id
                ._stock_disponible_para_traslado(
                    linea.product_id
                )
            )


    @api.onchange("product_id")
    def _onchange_producto_traslado(self):

        for linea in self:

            recepcion = linea.recepcion_id

            if (
                not recepcion
                or
                recepcion.tipo_entrada
                != "traslado_interno"
                or
                not linea.product_id
            ):

                continue

            linea.unidad_id = (
                linea.product_id.uom_id
            )

            linea.categoria_id = (
                linea.product_id.categ_id
            )

            stock = (
                recepcion
                ._stock_disponible_para_traslado(
                    linea.product_id
                )
            )

            if stock <= 0:

                return {
                    "warning": {

                        "title":
                            "Producto sin stock",

                        "message":
                            (
                                "El producto "
                                f"'{linea.product_id.display_name}' "
                                "no tiene stock "
                                "disponible en el "
                                "grado que entrega."
                            ),
                    }
                }

    @api.constrains(
        "cantidad_entregada"
    )
    def _check_cantidad_traslado_entera(
        self
    ):

        for linea in self:

            if (
                not linea.recepcion_id
                or
                linea.recepcion_id.tipo_entrada
                != "traslado_interno"
            ):

                continue

            cantidad = float(
                linea.cantidad_entregada
                or 0
            )

            if cantidad < 0:

                raise ValidationError(
                    "La cantidad saliente no "
                    "puede ser negativa."
                )

            if not cantidad.is_integer():

                raise ValidationError(
                    "La cantidad saliente debe "
                    "ser un número entero. "
                    "No se permiten decimales."
                )

    @api.onchange("cantidad_entregada")
    def _onchange_advertir_cantidad_incorrecta(self):

        for linea in self:

            cantidad = float(
                linea.cantidad_entregada or 0
            )

            cantidad_requerida = float(
                linea.cantidad_esperada or 0
            )

            producto = (
                linea.product_id.display_name
                or "Producto sin nombre"
            )

            tipo_entrada = (
                linea.recepcion_id.tipo_entrada
                if linea.recepcion_id
                else False
            )

            # Negativos: se validan
            # en todos los tipos de entrada
            if cantidad < 0:

                return {
                    "warning": {
                        "title":
                            "Cantidad negativa",

                        "message": (
                            f"El producto '{producto}' "
                            f"tiene la cantidad "
                            f"{cantidad:g}.\n\n"
                            "No se permiten números "
                            "negativos."
                        ),
                    }
                }

            # Decimales: se validan
            # en todos los tipos
            if not cantidad.is_integer():

                return {
                    "warning": {
                        "title":
                            "Cantidad decimal",

                        "message": (
                            f"El producto '{producto}' "
                            f"tiene la cantidad "
                            f"{cantidad:g}.\n\n"
                            "Solo se permiten "
                            "números enteros."
                        ),
                    }
                }

            # El máximo solo se aplica
            # a recepción por matrícula
            if (
                tipo_entrada
                == "recepcion_utiles"
                and
                cantidad
                > cantidad_requerida
            ):

                return {
                    "warning": {
                        "title":
                            "Cantidad superior",

                        "message": (
                            f"El producto '{producto}' "
                            f"requiere "
                            f"{cantidad_requerida:g}, "
                            f"pero se ingresó "
                            f"{cantidad:g}."
                        ),
                    }
                }

    @api.constrains(
        "cantidad_entregada",
        "cantidad_esperada",
        "unidad_id"
    )
    def _check_cantidad_entregada_valida(self):

        errores = []

        for linea in self:

            producto = (
                linea.product_id.display_name
                or "Producto sin nombre"
            )

            cantidad = float(
                linea.cantidad_entregada or 0
            )

            cantidad_requerida = float(
                linea.cantidad_esperada or 0
            )

            tipo_entrada = (
                linea.recepcion_id.tipo_entrada
                if linea.recepcion_id
                else False
            )

            if cantidad < 0:

                errores.append(
                    f"{producto}: no se permiten "
                    f"cantidades negativas."
                )

            elif not cantidad.is_integer():

                errores.append(
                    f"{producto}: se ingresó "
                    f"{cantidad:g}, pero solo se "
                    f"permiten números enteros."
                )

            elif (
                tipo_entrada
                == "recepcion_utiles"
                and
                cantidad
                > cantidad_requerida
            ):

                errores.append(
                    f"{producto}: se ingresó "
                    f"{cantidad:g}, pero la cantidad "
                    f"máxima permitida es "
                    f"{cantidad_requerida:g}."
                )

            if (
                tipo_entrada
                == "compra_directa"
                and
                not linea.unidad_id
            ):

                errores.append(
                    f"{producto}: debe seleccionar "
                    f"una unidad."
                )

        if errores:

            detalle = "\n".join(
                f"• {error}"
                for error in errores
            )

            raise ValidationError(
                "No se puede guardar porque "
                "existen inconsistencias:"
                "\n\n"
                f"{detalle}"
                "\n\n"
                "Corrija los productos indicados."
            )

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

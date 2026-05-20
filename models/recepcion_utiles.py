from odoo import models, fields, api
from odoo.exceptions import UserError


class RecepcionUtilesEscolar(models.Model):
    _name = "recepcion.utiles.escolar"
    _description = "Recepción de útiles escolares"
    _rec_name = "name"
    _order = "fecha desc, id desc"

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

    linea_ids = fields.One2many(
        "recepcion.utiles.linea",
        "recepcion_id",
        string="Productos recibidos"
    )

    estado = fields.Selection(
        [
            ("borrador", "Borrador"),
            ("incompleto", "Incompleto"),
            ("completo", "Completo"),
            ("validado", "Validado"),
        ],
        string="Estado",
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

    estado_almacen = fields.Selection(
    [
        ("pendiente", "Pendiente"),
        ("enviado", "Productos de almacén enviados"),
        ("sin_productos", "Sin productos para almacén"),
    ],
    string="Estado de almacén",
    default="pendiente",
    readonly=True
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

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "Nueva") == "Nueva":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "recepcion.utiles.escolar"
                ) or "Nueva"
        return super().create(vals_list)

    @api.depends(
        "linea_ids.estado_linea",
        "linea_ids.cantidad_faltante",
        "linea_ids.cantidad_entregada",
    )

    def action_recalcular_destinos(self):
        for rec in self:
            for linea in rec.linea_ids:
                linea.destino_recepcion = rec._calcular_destino_recepcion(linea.tipo_uso_escolar)

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

    def _obtener_valor_linea(self, linea, posibles_campos, valor_default=False):
        for campo in posibles_campos:
            if campo in linea._fields:
                return linea[campo]
        return valor_default

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

                comandos.append((0, 0, {
                    "product_id": producto.id,
                    "cantidad_esperada": cantidad,
                    "cantidad_entregada": 0,
                    "unidad_id": unidad.id if unidad else False,
                    "categoria_id": categoria.id if categoria else False,
                    "tipo_uso_escolar": tipo_uso_texto,
                    "destino_recepcion": rec._calcular_destino_recepcion(tipo_uso_texto),
                    "observacion": observacion,
                }))

            rec.write({
                "linea_ids": comandos,
                "estado": "borrador",
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


    def _calcular_destino_recepcion(self, tipo_uso):
        texto = (tipo_uso or "").lower().strip()

        # Útiles que se quedan con el estudiante
        if (
            "personal" in texto
             or "util personal" in texto
             or "útil personal" in texto
             or "niño" in texto
             or "niña" in texto
             or "estudiante" in texto
        ):
            return "estudiante"

        # Todo lo demás pasa a almacén
        return "almacen"


    def action_enviar_productos_almacen(self):
        for rec in self:
            if rec.estado != "validado":
               raise UserError("Solo puedes enviar a almacén una recepción validada.")

            productos_almacen = rec.linea_ids.filtered(
               lambda l: l.destino_recepcion == "almacen" and l.cantidad_entregada > 0
        )

        if not productos_almacen:
            rec.write({
                "estado_almacen": "sin_productos",
                "fecha_envio_almacen": fields.Datetime.now(),
                "usuario_envio_almacen_id": self.env.user.id,
            })
            return

        rec.write({
            "estado_almacen": "enviado",
            "fecha_envio_almacen": fields.Datetime.now(),
            "usuario_envio_almacen_id": self.env.user.id,
        })


class RecepcionUtilesLinea(models.Model):
    _name = "recepcion.utiles.linea"
    _description = "Detalle de recepción de útiles escolares"

    destino_recepcion = fields.Selection(
    [
        ("estudiante", "Se queda con estudiante"),
        ("almacen", "Enviar a almacén"),
    ],
    string="Destino",
    default="almacen"
   )

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

    @api.onchange("tipo_uso_escolar")
    def _onchange_tipo_uso_escolar_destino(self):
        for rec in self:
            texto = (rec.tipo_uso_escolar or "").lower()

            if "personal" in texto or "niño" in texto or "estudiante" in texto:
                rec.destino_recepcion = "estudiante"
            else:
                rec.destino_recepcion = "almacen"
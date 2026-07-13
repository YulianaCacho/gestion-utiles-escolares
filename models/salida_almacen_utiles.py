from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


# ============================================================
# CONSTANTES
# ============================================================

GRADOS_ESCOLARES = [
    ("inicial_3", "Inicial 3 años"),
    ("inicial_4", "Inicial 4 años"),
    ("inicial_5", "Inicial 5 años"),
    ("1er_grado", "1er grado"),
    ("2do_grado", "2do grado"),
    ("3er_grado", "3er grado"),
    ("4to_grado", "4to grado"),
    ("5to_grado", "5to grado"),
    ("6to_grado", "6to grado"),
]

CARGOS_QUE_ENTREGAN = [
    "promotora",
    "directora",
    "secretaria",
    "coordinadora",
]

CARGOS_QUE_RECIBEN = [
    "docente",
    "auxiliar_recepcion",
]


# ============================================================
# ENTREGA DE ÚTILES DESDE ALMACÉN
# ============================================================

class SalidaAlmacenUtiles(models.Model):

    _name = "salida.almacen.utiles"
    _description = "Entrega de útiles desde almacén"
    _order = "fecha_salida desc, id desc"


    # --------------------------------------------------------
    # DATOS GENERALES
    # --------------------------------------------------------

    name = fields.Char(
        string="Código de entrega",
        default="Nueva",
        readonly=True,
        copy=False,
    )

    fecha_salida = fields.Datetime(
        string="Fecha y hora de entrega",
        default=fields.Datetime.now,
        required=True,
    )

    responsable_id = fields.Many2one(
        "res.partner",
        string="Quién entrega",
        required=True,
        domain=[
            ("tipo_contacto_escolar", "=", "personal"),
            (
                "cargo_institucional",
                "in",
                CARGOS_QUE_ENTREGAN,
            ),
        ],
        ondelete="restrict",
    )

    miss_id = fields.Many2one(
        "res.partner",
        string="Docente / auxiliar que recibe",
        required=True,
        domain=[
            ("tipo_contacto_escolar", "=", "personal"),
            (
                "cargo_institucional",
                "in",
                CARGOS_QUE_RECIBEN,
            ),
        ],
        ondelete="restrict",
    )

    grado_escolar = fields.Selection(
        selection=GRADOS_ESCOLARES,
        string="Grado escolar",
        required=True,
    )

    linea_ids = fields.One2many(
        "salida.almacen.utiles.linea",
        "salida_id",
        string="Productos entregados",
    )

    observacion = fields.Text(
        string="Observación",
    )


    # --------------------------------------------------------
    # CONTROL Y ESTADO
    # --------------------------------------------------------

    estado = fields.Selection(
        [
            ("borrador", "Borrador"),
            ("validado", "Validado"),
        ],
        string="Estado",
        default="borrador",
        required=True,
        copy=False,
    )

    user_id = fields.Many2one(
        "res.users",
        string="Usuario que registró",
        default=lambda self: self.env.user,
        readonly=True,
        copy=False,
    )


    # --------------------------------------------------------
    # TOTALES
    # --------------------------------------------------------

    total_productos = fields.Integer(
        string="Total de productos",
        compute="_compute_totales",
        store=True,
    )

    total_cantidad = fields.Float(
        string="Cantidad total entregada",
        compute="_compute_totales",
        store=True,
    )


    # ========================================================
    # MÉTODOS COMPUTADOS
    # ========================================================

    @api.depends(
        "linea_ids",
        "linea_ids.cantidad",
    )
    def _compute_totales(self):

        for rec in self:

            rec.total_productos = len(
                rec.linea_ids
            )

            rec.total_cantidad = sum(
                rec.linea_ids.mapped(
                    "cantidad"
                )
            )


    # ========================================================
    # CREACIÓN
    # ========================================================

    @api.model_create_multi
    def create(self, vals_list):

        for vals in vals_list:

            if vals.get(
                "name",
                "Nueva",
            ) == "Nueva":

                vals["name"] = (
                    self.env[
                        "ir.sequence"
                    ].next_by_code(
                        "salida.almacen.utiles"
                    )
                    or
                    "Nueva"
                )

        return super().create(
            vals_list
        )


    # ========================================================
    # ONCHANGE
    # ========================================================

    @api.onchange("miss_id")
    def _onchange_miss_id(self):

        for rec in self:

            if (
                rec.miss_id
                and
                rec.miss_id.grado_escolar
            ):

                rec.grado_escolar = (
                    rec.miss_id.grado_escolar
                )

            elif not rec.miss_id:

                rec.grado_escolar = False


    # ========================================================
    # VALIDACIÓN DEL RECEPTOR
    # ========================================================

    def _receptor_es_valido(self):

        self.ensure_one()

        if not self.miss_id:

            return False

        return (
            self.miss_id.tipo_contacto_escolar
            ==
            "personal"
            and
            self.miss_id.cargo_institucional
            in
            CARGOS_QUE_RECIBEN
        )


    @api.constrains("miss_id")
    def _check_receptor_permitido(self):

        for rec in self:

            if (
                rec.miss_id
                and
                not rec._receptor_es_valido()
            ):

                raise ValidationError(
                    "La persona que recibe debe "
                    "pertenecer al personal de la "
                    "institución y tener el cargo "
                    "de Docente o Auxiliar."
                )


    # ========================================================
    # CÁLCULO DE STOCK
    # ========================================================

    def _stock_disponible_producto(
        self,
        producto,
    ):

        self.ensure_one()

        if not producto:

            return 0.0

        dominio = [
            (
                "product_id",
                "=",
                producto.id,
            ),
        ]

        if self.anio_escolar_id:

            dominio.append(
                (
                    "anio_escolar_id",
                    "=",
                    self.anio_escolar_id.id,
                )
            )

        movimientos = self.env[
            "almacen.utiles.movimiento"
        ].search(
            dominio
        )

        stock = 0.0

        for movimiento in movimientos:

            cantidad = float(
                movimiento.cantidad
                or
                0
            )

            if (
                movimiento.tipo_movimiento
                ==
                "entrada"
            ):

                stock += cantidad

            elif (
                movimiento.tipo_movimiento
                ==
                "salida"
            ):

                stock -= cantidad

            elif (
                movimiento.tipo_movimiento
                ==
                "ajuste"
            ):

                stock += cantidad

        return stock


    # ========================================================
    # VALIDACIONES DE LA ENTREGA
    # ========================================================

    def _validar_datos_generales(self):

        self.ensure_one()

        errores = []

        if not self.responsable_id:

            errores.append(
                "Debe seleccionar a la persona "
                "que realiza la entrega."
            )

        if not self.miss_id:

            errores.append(
                "Debe seleccionar al docente "
                "o auxiliar que recibe."
            )

        elif not self._receptor_es_valido():

            errores.append(
                "La persona que recibe debe "
                "tener el cargo de Docente "
                "o Auxiliar."
            )

        if not self.grado_escolar:

            errores.append(
                "Debe seleccionar el grado "
                "que recibe los útiles."
            )

        if not self.linea_ids:

            errores.append(
                "Debe agregar al menos un "
                "producto."
            )

        return errores


    def _validar_productos_y_stock(self):

        self.ensure_one()

        errores = []

        cantidades_por_producto = {}

        for linea in self.linea_ids:

            if not linea.product_id:

                errores.append(
                    "Existe una línea sin "
                    "producto seleccionado."
                )

                continue

            producto = (
                linea.product_id.display_name
                or
                "Producto sin nombre"
            )

            cantidad = float(
                linea.cantidad
                or
                0
            )

            if cantidad <= 0:

                errores.append(
                    f"{producto}: la cantidad "
                    "entregada debe ser mayor "
                    "que cero."
                )

                continue

            if not cantidad.is_integer():

                errores.append(
                    f"{producto}: la cantidad "
                    f"{cantidad:g} contiene "
                    "decimales. Solo se permiten "
                    "números enteros."
                )

                continue

            cantidades_por_producto[
                linea.product_id.id
            ] = (
                cantidades_por_producto.get(
                    linea.product_id.id,
                    0,
                )
                +
                cantidad
            )


        for (
            producto_id,
            cantidad_solicitada,
        ) in cantidades_por_producto.items():

            producto = self.env[
                "product.product"
            ].browse(
                producto_id
            )

            stock_disponible = (
                self._stock_disponible_producto(
                    producto
                )
            )

            nombre_producto = (
                producto.display_name
                or
                "Producto sin nombre"
            )

            if stock_disponible <= 0:

                errores.append(
                    f"{nombre_producto}: "
                    "el producto no tiene "
                    "stock disponible. No se "
                    "puede registrar la salida."
                )

            elif (
                cantidad_solicitada
                >
                stock_disponible
            ):

                errores.append(
                    f"{nombre_producto}: "
                    f"se intentó retirar "
                    f"{cantidad_solicitada:g}, "
                    "pero el stock disponible "
                    f"es {stock_disponible:g}."
                )

        return errores


    def _mostrar_errores_validacion(
        self,
        errores,
    ):

        if not errores:

            return

        detalle = "\n".join(
            f"• {error}"
            for error in errores
        )

        raise ValidationError(
            "No se puede validar la entrega "
            "porque existen inconsistencias:"
            "\n\n"
            f"{detalle}"
            "\n\n"
            "Corrija los datos indicados "
            "y vuelva a validar."
        )


    # ========================================================
    # CREACIÓN DEL MOVIMIENTO DE SALIDA
    # ========================================================

    def _crear_movimiento_salida(
        self,
        linea,
    ):

        self.ensure_one()

        grado_texto = dict(
            GRADOS_ESCOLARES
        ).get(
            self.grado_escolar,
            self.grado_escolar,
        )

        valores = {

            "tipo_movimiento":
                "salida",

            "anio_escolar_id":
                (
                    self.anio_escolar_id.id
                    if
                    self.anio_escolar_id
                    else
                    False
                ),

            "salida_almacen_id":
                self.id,

            "grado_escolar":
                self.grado_escolar,

            "product_id":
                linea.product_id.id,

            "cantidad":
                linea.cantidad,

            "unidad_id":
                (
                    linea.unidad_id.id
                    if
                    linea.unidad_id
                    else
                    False
                ),

            "categoria_id":
                (
                    linea.categoria_id.id
                    if
                    linea.categoria_id
                    else
                    False
                ),

            "responsable_id":
                self.env.user.id,

            "destino":
                (
                    f"{self.miss_id.name}"
                    f" - "
                    f"{grado_texto}"
                ),

            "observacion":
                (
                    f"Entrega registrada en "
                    f"{self.name}. "
                    f"Entrega: "
                    f"{self.responsable_id.name}. "
                    f"Recibe: "
                    f"{self.miss_id.name}. "
                    f"Grado: "
                    f"{grado_texto}."
                ),
        }

        self.env[
            "almacen.utiles.movimiento"
        ].create(
            valores
        )


    # ========================================================
    # ACCIÓN: VALIDAR ENTREGA
    # ========================================================

    def action_validar_salida(self):

        for rec in self:

            if (
                rec.estado
                ==
                "validado"
            ):

                raise UserError(
                    "Esta entrega ya fue "
                    "validada."
                )

            errores = []

            errores.extend(
                rec._validar_datos_generales()
            )

            errores.extend(
                rec._validar_productos_y_stock()
            )

            rec._mostrar_errores_validacion(
                errores
            )


            for linea in rec.linea_ids:

                rec._crear_movimiento_salida(
                    linea
                )


            rec.write(
                {
                    "estado":
                        "validado"
                }
            )


        return {

            "type":
                "ir.actions.client",

            "tag":
                "display_notification",

            "params": {

                "title":
                    "Entrega validada",

                "message":
                    (
                        "La salida fue registrada "
                        "correctamente y ya aparece "
                        "en la línea de tiempo."
                    ),

                "type":
                    "success",

                "sticky":
                    False,
            },
        }


# ============================================================
# LÍNEAS DE LA ENTREGA
# ============================================================

class SalidaAlmacenUtilesLinea(models.Model):

    _name = "salida.almacen.utiles.linea"

    _description = (
        "Detalle de entrega de útiles "
        "desde almacén"
    )


    # --------------------------------------------------------
    # CAMPOS
    # --------------------------------------------------------

    salida_id = fields.Many2one(
        "salida.almacen.utiles",
        string="Entrega",
        required=True,
        ondelete="cascade",
    )

    product_id = fields.Many2one(
        "product.product",
        string="Producto",
        required=True,
    )

    cantidad = fields.Float(
        string="Cantidad entregada",
        required=True,
        default=1,
    )

    unidad_id = fields.Many2one(
        "uom.uom",
        string="Unidad",
        related="product_id.uom_id",
        readonly=True,
    )

    categoria_id = fields.Many2one(
        "product.category",
        string="Categoría",
        related="product_id.categ_id",
        readonly=True,
    )

    stock_disponible = fields.Float(
        string="Stock disponible",
        compute="_compute_stock_disponible",
    )

    observacion = fields.Char(
        string="Observación",
    )


    # ========================================================
    # STOCK DISPONIBLE
    # ========================================================

    @api.depends(
        "product_id",
        "salida_id.anio_escolar_id",
    )
    def _compute_stock_disponible(self):

        for linea in self:

            if (
                not linea.product_id
                or
                not linea.salida_id
            ):

                linea.stock_disponible = 0

                continue

            linea.stock_disponible = (
                linea.salida_id
                ._stock_disponible_producto(
                    linea.product_id
                )
            )


    # ========================================================
    # ADVERTENCIA AL ELEGIR PRODUCTO
    # ========================================================

    @api.onchange("product_id")
    def _onchange_producto_stock(self):

        for linea in self:

            if (
                not linea.product_id
                or
                not linea.salida_id
            ):

                continue

            stock_disponible = (
                linea.salida_id
                ._stock_disponible_producto(
                    linea.product_id
                )
            )

            if stock_disponible <= 0:

                return {

                    "warning": {

                        "title":
                            "Producto sin stock",

                        "message":
                            (
                                "El producto "
                                f"'{linea.product_id.display_name}' "
                                "no tiene stock "
                                "disponible. No se "
                                "puede registrar "
                                "una salida."
                            ),
                    },
                }


    # ========================================================
    # ADVERTENCIAS DE CANTIDAD
    # ========================================================

    @api.onchange("cantidad")
    def _onchange_cantidad(self):

        for linea in self:

            cantidad = float(
                linea.cantidad
                or
                0
            )


            if cantidad <= 0:

                return {

                    "warning": {

                        "title":
                            "Cantidad incorrecta",

                        "message":
                            (
                                "La cantidad entregada "
                                "debe ser mayor que "
                                "cero."
                            ),
                    },
                }


            if not cantidad.is_integer():

                return {

                    "warning": {

                        "title":
                            "Cantidad decimal",

                        "message":
                            (
                                "Solo se permiten "
                                "números enteros. "
                                "No se permiten "
                                "cantidades decimales."
                            ),
                    },
                }


            if (
                linea.product_id
                and
                linea.salida_id
            ):

                stock_disponible = (
                    linea.salida_id
                    ._stock_disponible_producto(
                        linea.product_id
                    )
                )

                if (
                    cantidad
                    >
                    stock_disponible
                ):

                    return {

                        "warning": {

                            "title":
                                "Stock insuficiente",

                            "message":
                                (
                                    f"La cantidad "
                                    f"ingresada es "
                                    f"{cantidad:g}, "
                                    "pero el stock "
                                    "disponible es "
                                    f"{stock_disponible:g}."
                                ),
                        },
                    }


    # ========================================================
    # RESTRICCIONES
    # ========================================================

    @api.constrains(
        "cantidad",
        "product_id",
        "salida_id",
    )
    def _check_cantidad(self):

        for linea in self:

            if not linea.product_id:

                continue

            cantidad = float(
                linea.cantidad
                or
                0
            )

            if cantidad <= 0:

                raise ValidationError(
                    "La cantidad entregada "
                    "debe ser mayor que cero."
                )

            if not cantidad.is_integer():

                raise ValidationError(
                    "La cantidad entregada "
                    "debe ser un número entero. "
                    "No se permiten decimales."
                )

            if not linea.salida_id:

                continue

            stock_disponible = (
                linea.salida_id
                ._stock_disponible_producto(
                    linea.product_id
                )
            )

            if stock_disponible <= 0:

                raise ValidationError(
                    f"El producto "
                    f"'{linea.product_id.display_name}' "
                    "no tiene stock disponible. "
                    "No se puede registrar "
                    "una salida."
                )

            if (
                cantidad
                >
                stock_disponible
            ):

                raise ValidationError(
                    "No hay stock suficiente "
                    f"para "
                    f"'{linea.product_id.display_name}'."
                    "\n\n"
                    f"Stock disponible: "
                    f"{stock_disponible:g}"
                    "\n"
                    f"Cantidad solicitada: "
                    f"{cantidad:g}"
                )


# ============================================================
# RELACIÓN CON MOVIMIENTOS DE ALMACÉN
# ============================================================

class AlmacenUtilesMovimiento(models.Model):

    _inherit = "almacen.utiles.movimiento"


    salida_almacen_id = fields.Many2one(
        "salida.almacen.utiles",
        string="Entrega relacionada",
        ondelete="cascade",
    )
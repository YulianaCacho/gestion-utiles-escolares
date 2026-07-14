from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


GRADO_ESCOLAR_SELECTION = [
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


class RecepcionUtilesSobranteAnio(models.Model):
    _inherit = "recepcion.utiles.escolar"

    tipo_entrada = fields.Selection(
        selection_add=[
            (
                "sobrante_anio_anterior",
                "Útiles sobrantes del año anterior",
            ),
        ],
        ondelete={
            "sobrante_anio_anterior": "set default",
        },
    )

    grado_entrada_sobrante = fields.Selection(
        GRADO_ESCOLAR_SELECTION,
        string="Grado de los sobrantes",
        readonly=True,
        copy=False,
    )

    cierre_anio_utiles_id = fields.Many2one(
        "cierre.anio.utiles",
        string="Cierre de útiles relacionado",
        readonly=True,
        copy=False,
        ondelete="set null",
    )


class CierreAnioUtiles(models.Model):
    _name = "cierre.anio.utiles"
    _description = "Cierre de año y revisión de sobrantes"
    _order = "anio_origen_id desc, id desc"

    name = fields.Char(
        string="Referencia",
        compute="_compute_name",
        store=True,
    )

    anio_origen_id = fields.Many2one(
        "anio.escolar",
        string="Año a cerrar",
        required=True,
        readonly=True,
        ondelete="restrict",
    )

    anio_destino_id = fields.Many2one(
        "anio.escolar",
        string="Año siguiente",
        required=False,
        readonly=True,
        copy=False,
        ondelete="set null",
        help=(
            "Se asignará cuando se cree el siguiente "
            "año escolar y se revise el ingreso "
            "de los útiles sobrantes."
        ),
    )

    fecha_revision = fields.Datetime(
        string="Fecha de revisión",
        default=fields.Datetime.now,
        required=True,
    )

    fecha_validacion_cierre = fields.Datetime(
        string="Fecha de validación del cierre",
        readonly=True,
        copy=False,
    )

    fecha_confirmacion = fields.Datetime(
        string="Fecha de ingreso al nuevo año",
        readonly=True,
        copy=False,
    )

    responsable_id = fields.Many2one(
        "res.users",
        string="Responsable",
        default=lambda self: self.env.user,
        required=True,
        readonly=True,
    )

    estado = fields.Selection(
        [
            (
                "borrador",
                "Borrador",
            ),
            (
                "revision",
                "Revisión de cierre",
            ),
            (
                "cierre_validado",
                "Cierre validado",
            ),
            (
                "ingreso_revision",
                "Revisión de ingreso",
            ),
            (
                "confirmado",
                "Ingreso confirmado",
            ),
        ],
        string="Estado",
        default="borrador",
        required=True,
        copy=False,
    )

    linea_ids = fields.One2many(
        "cierre.anio.utiles.linea",
        "cierre_id",
        string="Útiles sobrantes revisados",
        copy=False,
    )

    total_productos = fields.Integer(
        string="Productos revisados",
        compute="_compute_totales",
    )

    total_sistema = fields.Float(
        string="Cantidad según sistema",
        compute="_compute_totales",
    )

    total_trasladar = fields.Float(
        string="Cantidad enviada",
        compute="_compute_totales",
    )

    total_no_aprovechable = fields.Float(
        string="Cantidad no aprovechable",
        compute="_compute_totales",
    )

    total_recibido = fields.Float(
        string="Cantidad recibida",
        compute="_compute_totales",
    )

    observacion = fields.Text(
        string="Observación general",
    )

    @api.depends(
        "anio_origen_id",
        "anio_destino_id",
    )
    def _compute_name(self):

        for rec in self:

            origen = (
                rec.anio_origen_id.name
                or
                ""
            )

            destino = (
                rec.anio_destino_id.name
                or
                ""
            )

            if origen and destino:

                rec.name = (
                    f"Cierre de útiles "
                    f"{origen} → {destino}"
                )

            elif origen:

                rec.name = (
                    f"Cierre de útiles "
                    f"{origen}"
                )

            else:

                rec.name = (
                    "Cierre de útiles"
                )

    @api.depends(
        "linea_ids",
        "linea_ids.cantidad_sistema",
        "linea_ids.cantidad_a_trasladar",
        "linea_ids.cantidad_no_aprovechable",
        "linea_ids.cantidad_recibida",
    )
    def _compute_totales(self):

        for rec in self:

            rec.total_productos = len(
                rec.linea_ids
            )

            rec.total_sistema = sum(
                rec.linea_ids.mapped(
                    "cantidad_sistema"
                )
            )

            rec.total_trasladar = sum(
                rec.linea_ids.mapped(
                    "cantidad_a_trasladar"
                )
            )

            rec.total_no_aprovechable = sum(
                rec.linea_ids.mapped(
                    "cantidad_no_aprovechable"
                )
            )

            rec.total_recibido = sum(
                rec.linea_ids.mapped(
                    "cantidad_recibida"
                )
            )

    def _fmt_qty(
        self,
        value,
    ):

        value = float(
            value
            or
            0
        )

        if value.is_integer():

            return str(
                int(value)
            )

        return (
            f"{value:.2f}"
            .rstrip("0")
            .rstrip(".")
        )

    def _action_abrir_formulario(self):

        self.ensure_one()

        return {
            "type":
                "ir.actions.act_window",

            "name":
                (
                    "Cierre de año y "
                    "revisión de sobrantes"
                ),

            "res_model":
                "cierre.anio.utiles",

            "view_mode":
                "form",

            "res_id":
                self.id,

            "target":
                "current",
        }

    def _calcular_saldos_por_producto_grado(
        self
    ):

        self.ensure_one()

        Movimiento = self.env[
            "almacen.utiles.movimiento"
        ]

        movimientos = Movimiento.search(
            [
                (
                    "anio_escolar_id",
                    "=",
                    self.anio_origen_id.id,
                ),
                (
                    "product_id",
                    "!=",
                    False,
                ),
            ]
        )

        saldos = {}

        for movimiento in movimientos:

            clave = (
                movimiento.product_id.id,
                movimiento.grado_escolar
                or
                False,
            )

            if clave not in saldos:

                saldos[clave] = {
                    "product_id":
                        movimiento.product_id.id,

                    "grado_escolar":
                        movimiento.grado_escolar
                        or
                        False,

                    "cantidad":
                        0.0,
                }

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

                saldos[clave][
                    "cantidad"
                ] += cantidad

            elif (
                movimiento.tipo_movimiento
                ==
                "salida"
            ):

                saldos[clave][
                    "cantidad"
                ] -= cantidad

            elif (
                movimiento.tipo_movimiento
                ==
                "ajuste"
            ):

                saldos[clave][
                    "cantidad"
                ] += cantidad

        return [
            saldo
            for saldo
            in saldos.values()
            if saldo["cantidad"] > 0
        ]

    def _validar_revision_matriculas(
        self
    ):

        self.ensure_one()

        revision = self.env[
            "cierre.anio.matriculas"
        ].search(
            [
                (
                    "anio_origen_id",
                    "=",
                    self.anio_origen_id.id,
                ),
                (
                    "estado",
                    "=",
                    "confirmado",
                ),
            ],
            order=(
                "fecha_confirmacion "
                "desc, id desc"
            ),
            limit=1,
        )

        if not revision:

            raise UserError(
                "Primero debes validar los "
                "resultados de promoción de "
                "los estudiantes."
                "\n\n"
                "La revisión de matrículas "
                "debe estar en estado "
                "'Confirmado' antes de cerrar "
                "los útiles del año."
            )

        return revision

    def action_generar_revision(
        self
    ):

        self.ensure_one()

        if self.estado != "borrador":

            raise UserError(
                "La revisión de sobrantes "
                "ya fue generada."
                "\n\n"
                "No se puede volver a generar "
                "porque podrían perderse los "
                "cambios realizados."
            )

        if (
            self.anio_origen_id.estado
            !=
            "activo"
        ):

            raise UserError(
                "Solo se puede generar la "
                "revisión desde el año "
                "escolar activo."
            )

        saldos = (
            self
            ._calcular_saldos_por_producto_grado()
        )

        comandos = [
            (
                5,
                0,
                0,
            )
        ]

        for saldo in saldos:

            comandos.append(
                (
                    0,
                    0,
                    {
                        "product_id":
                            saldo[
                                "product_id"
                            ],

                        "grado_escolar":
                            saldo[
                                "grado_escolar"
                            ],

                        "cantidad_sistema":
                            saldo[
                                "cantidad"
                            ],

                        "cantidad_revisada":
                            saldo[
                                "cantidad"
                            ],

                        "cantidad_a_trasladar":
                            saldo[
                                "cantidad"
                            ],

                        "cantidad_recibida":
                            0,

                        "motivo_ajuste":
                            "no_aplica",
                    },
                )
            )

        self.write(
            {
                "linea_ids":
                    comandos,

                "estado":
                    "revision",
            }
        )

        return (
            self
            ._action_abrir_formulario()
        )

    def _validar_lineas_cierre(
        self
    ):

        self.ensure_one()

        for linea in self.linea_ids:

            if (
                linea.cantidad_revisada
                <
                0
            ):

                raise UserError(
                    "La cantidad revisada "
                    "no puede ser negativa."
                )

            if (
                linea.cantidad_a_trasladar
                <
                0
            ):

                raise UserError(
                    "La cantidad a trasladar "
                    "no puede ser negativa."
                )

            if (
                linea.cantidad_revisada
                >
                linea.cantidad_sistema
            ):

                raise UserError(
                    "La cantidad revisada "
                    "no puede ser mayor a la "
                    "cantidad registrada por "
                    "el sistema."
                    "\n\n"
                    f"Producto: "
                    f"{linea.product_id.display_name}"
                )

            if (
                linea.cantidad_a_trasladar
                >
                linea.cantidad_revisada
            ):

                raise UserError(
                    "La cantidad a trasladar "
                    "no puede ser mayor a la "
                    "cantidad revisada "
                    "físicamente."
                    "\n\n"
                    f"Producto: "
                    f"{linea.product_id.display_name}"
                )

            if (
                linea.cantidad_no_aprovechable
                >
                0
                and
                linea.motivo_ajuste
                ==
                "no_aplica"
            ):

                raise UserError(
                    "Debes seleccionar un "
                    "motivo para la cantidad "
                    "no aprovechable."
                    "\n\n"
                    f"Producto: "
                    f"{linea.product_id.display_name}"
                )

    def action_validar_cierre(
        self
    ):

        self.ensure_one()

        if self.estado != "revision":

            raise UserError(
                "El cierre de útiles solo "
                "puede validarse cuando se "
                "encuentra en revisión."
            )

        if (
            self.anio_origen_id.estado
            !=
            "activo"
        ):

            raise UserError(
                "El año escolar de origen "
                "debe estar activo."
            )

        self._validar_revision_matriculas()

        self._validar_lineas_cierre()

        Movimiento = self.env[
            "almacen.utiles.movimiento"
        ]

        for linea in self.linea_ids:

            producto = (
                linea.product_id
            )

            grado = (
                linea.grado_escolar
                or
                False
            )

            cantidad_trasladar = float(
                linea.cantidad_a_trasladar
                or
                0
            )

            cantidad_no_aprovechable = (
                float(
                    linea
                    .cantidad_no_aprovechable
                    or
                    0
                )
            )

            base_vals = {
                "product_id":
                    producto.id,

                "unidad_id":
                    (
                        producto.uom_id.id
                        if
                        producto.uom_id
                        else
                        False
                    ),

                "categoria_id":
                    (
                        producto.categ_id.id
                        if
                        producto.categ_id
                        else
                        False
                    ),

                "grado_escolar":
                    grado,

                "responsable_id":
                    self.env.user.id,

                "anio_escolar_id":
                    self.anio_origen_id.id,

                "anio_origen_id":
                    self.anio_origen_id.id,

                "anio_destino_id":
                    False,
            }

            if (
                cantidad_no_aprovechable
                >
                0
            ):

                motivo_label = dict(
                    linea
                    ._fields[
                        "motivo_ajuste"
                    ]
                    .selection
                ).get(
                    linea.motivo_ajuste,
                    (
                        "Ajuste por "
                        "cierre de año"
                    ),
                )

                Movimiento.create(
                    {
                        **base_vals,

                        "tipo_movimiento":
                            "ajuste",

                        "cantidad":
                            (
                                -cantidad_no_aprovechable
                            ),

                        "destino":
                            (
                                "Ajuste de "
                                "cierre de año"
                            ),

                        "observacion":
                            (
                                "Ajuste realizado "
                                f"durante el cierre "
                                f"de "
                                f"{self.anio_origen_id.name}. "
                                f"Motivo: "
                                f"{motivo_label}. "
                                f"Cantidad ajustada: "
                                f"{self._fmt_qty(cantidad_no_aprovechable)}."
                            ),
                    }
                )

            if (
                cantidad_trasladar
                >
                0
            ):

                Movimiento.create(
                    {
                        **base_vals,

                        "tipo_movimiento":
                            "salida",

                        "cantidad":
                            cantidad_trasladar,

                        "destino":
                            (
                                "Pendiente de "
                                "ingreso al "
                                "siguiente año"
                            ),

                        "observacion":
                            (
                                "Salida de fin de "
                                f"año desde "
                                f"{self.anio_origen_id.name}. "
                                "Los útiles quedan "
                                "pendientes de "
                                "revisión e ingreso "
                                "al siguiente "
                                "periodo escolar."
                            ),
                    }
                )

        self.write(
            {
                "estado":
                    "cierre_validado",

                "fecha_validacion_cierre":
                    fields.Datetime.now(),
            }
        )

        self.anio_origen_id.write(
            {
                "estado":
                    "cerrado",
            }
        )

        return (
            self
            ._action_abrir_formulario()
        )

    def _validar_lineas_ingreso(
        self
    ):

        self.ensure_one()

        for linea in self.linea_ids:

            if (
                linea.cantidad_recibida
                <
                0
            ):

                raise UserError(
                    "La cantidad recibida "
                    "no puede ser negativa."
                )

            if (
                linea.cantidad_recibida
                >
                linea.cantidad_a_trasladar
            ):

                raise UserError(
                    "La cantidad recibida "
                    "no puede ser mayor a la "
                    "cantidad enviada desde "
                    "el año anterior."
                    "\n\n"
                    f"Producto: "
                    f"{linea.product_id.display_name}"
                )

    def action_validar_ingreso(self):

        self.ensure_one()

        if self.estado != "ingreso_revision":
            raise UserError(
                "El ingreso solo puede validarse cuando se encuentra en revisión."
            )

        if not self.anio_destino_id:
            raise UserError(
                "No se ha asignado el año escolar de destino."
            )

        if self.anio_destino_id.estado != "activo":
            raise UserError(
                "El año escolar de destino debe estar activo."
            )

        self._validar_lineas_ingreso()

        Movimiento = self.env["almacen.utiles.movimiento"]
        Sobrante = self.env["sobrante.utiles.anio"]
        Recepcion = self.env["recepcion.utiles.escolar"]

        lineas_por_grado = {}

        for linea in self.linea_ids:
            cantidad_recibida = float(
                linea.cantidad_recibida or 0
            )

            if cantidad_recibida <= 0:
                continue

            grado = linea.grado_escolar or False
            lineas_por_grado.setdefault(
                grado,
                self.env["cierre.anio.utiles.linea"],
            )
            lineas_por_grado[grado] |= linea

        for grado, lineas_grado in lineas_por_grado.items():

            comandos_lineas = []

            for linea in lineas_grado:
                cantidad_recibida = float(
                    linea.cantidad_recibida or 0
                )

                comandos_lineas.append(
                    (
                        0,
                        0,
                        {
                            "product_id": linea.product_id.id,
                            "categoria_id": (
                                linea.product_id.categ_id.id
                                if linea.product_id.categ_id
                                else False
                            ),
                            "cantidad_esperada": cantidad_recibida,
                            "cantidad_entregada": cantidad_recibida,
                            "unidad_id": (
                                linea.product_id.uom_id.id
                                if linea.product_id.uom_id
                                else False
                            ),
                            "tipo_uso_escolar": (
                                "Sobrante del año anterior"
                            ),
                            "destino_recepcion": "almacen",
                            "cantidad_enviada_almacen": cantidad_recibida,
                            "observacion": (
                                f"Ingreso validado desde "
                                f"{self.anio_origen_id.name}."
                            ),
                        },
                    )
                )

            recepcion = Recepcion.create(
                {
                    "tipo_entrada": "sobrante_anio_anterior",
                    "anio_escolar_id": self.anio_destino_id.id,
                    "grado_entrada_sobrante": grado,
                    "cierre_anio_utiles_id": self.id,
                    "estado": "validado",
                    "observacion": (
                        "Ingreso de útiles sobrantes del año anterior. "
                        f"Origen: {self.anio_origen_id.name}. "
                        f"Destino: {self.anio_destino_id.name}."
                    ),
                    "linea_ids": comandos_lineas,
                }
            )

            lineas_recepcion_por_producto = {
                linea.product_id.id: linea
                for linea in recepcion.linea_ids
            }

            for linea in lineas_grado:

                cantidad_recibida = float(
                    linea.cantidad_recibida or 0
                )

                producto = linea.product_id
                linea_recepcion = (
                    lineas_recepcion_por_producto.get(
                        producto.id
                    )
                )

                valores_movimiento = {
                    "product_id": producto.id,
                    "unidad_id": (
                        producto.uom_id.id
                        if producto.uom_id
                        else False
                    ),
                    "categoria_id": (
                        producto.categ_id.id
                        if producto.categ_id
                        else False
                    ),
                    "grado_escolar": grado,
                    "responsable_id": self.env.user.id,
                    "anio_escolar_id": self.anio_destino_id.id,
                    "anio_origen_id": self.anio_origen_id.id,
                    "anio_destino_id": self.anio_destino_id.id,
                    "recepcion_id": recepcion.id,
                    "tipo_movimiento": "entrada",
                    "cantidad": cantidad_recibida,
                    "destino": "Almacén del nuevo periodo",
                    "observacion": (
                        "Ingreso de útiles sobrantes del año "
                        f"{self.anio_origen_id.name}. "
                        f"Cantidad enviada: "
                        f"{self._fmt_qty(linea.cantidad_a_trasladar)}. "
                        f"Cantidad recibida: "
                        f"{self._fmt_qty(cantidad_recibida)}."
                    ),
                }

                if (
                    linea_recepcion
                    and "recepcion_linea_id" in Movimiento._fields
                ):
                    valores_movimiento[
                        "recepcion_linea_id"
                    ] = linea_recepcion.id

                Movimiento.create(
                    valores_movimiento
                )

                sobrante = Sobrante.search(
                    [
                        (
                            "anio_origen_id",
                            "=",
                            self.anio_origen_id.id,
                        ),
                        (
                            "anio_destino_id",
                            "=",
                            self.anio_destino_id.id,
                        ),
                        (
                            "product_id",
                            "=",
                            producto.id,
                        ),
                        (
                            "grado_escolar",
                            "=",
                            grado,
                        ),
                    ],
                    limit=1,
                )

                vals_sobrante = {
                    "anio_origen_id": self.anio_origen_id.id,
                    "anio_destino_id": self.anio_destino_id.id,
                    "product_id": producto.id,
                    "grado_escolar": grado,
                    "cantidad_inicial": cantidad_recibida,
                    "cantidad_usada": 0,
                    "observacion": (
                        "Sobrante revisado y validado al iniciar "
                        f"{self.anio_destino_id.name}. "
                        f"Cantidad enviada: "
                        f"{self._fmt_qty(linea.cantidad_a_trasladar)}. "
                        f"Cantidad recibida: "
                        f"{self._fmt_qty(cantidad_recibida)}."
                    ),
                }

                if sobrante:
                    sobrante.write(
                        vals_sobrante
                    )
                else:
                    Sobrante.create(
                        vals_sobrante
                    )

        self.write(
            {
                "estado": "confirmado",
                "fecha_confirmacion": fields.Datetime.now(),
            }
        )

        return self._action_abrir_formulario()


class CierreAnioUtilesLinea(models.Model):
    _name = "cierre.anio.utiles.linea"
    _description = "Línea de revisión de sobrantes por cierre de año"
    _order = "grado_escolar, product_id"

    cierre_id = fields.Many2one(
        "cierre.anio.utiles",
        string="Cierre de año",
        required=True,
        ondelete="cascade",
    )

    product_id = fields.Many2one(
        "product.product",
        string="Producto",
        required=True,
        readonly=True,
    )

    categoria_id = fields.Many2one(
        "product.category",
        string="Categoría",
        related="product_id.categ_id",
        readonly=True,
    )

    uom_id = fields.Many2one(
        "uom.uom",
        string="Unidad",
        related="product_id.uom_id",
        readonly=True,
    )

    grado_escolar = fields.Selection(
        GRADO_ESCOLAR_SELECTION,
        string="Grado / sección",
        readonly=True,
    )

    cantidad_sistema = fields.Float(
        string="Cantidad según sistema",
        readonly=True,
    )

    cantidad_revisada = fields.Float(
        string="Cantidad revisada físicamente",
    )

    cantidad_a_trasladar = fields.Float(
        string="Cantidad enviada",
    )

    cantidad_no_aprovechable = fields.Float(
        string="No aprovechable / ajuste",
        compute="_compute_cantidad_no_aprovechable",
        store=True,
    )

    cantidad_recibida = fields.Float(
        string="Cantidad recibida",
        default=0.0,
    )

    diferencia_ingreso = fields.Float(
        string="Diferencia de ingreso",
        compute="_compute_diferencia_ingreso",
    )

    motivo_ajuste = fields.Selection(
        [
            (
                "no_aplica",
                "No aplica",
            ),
            (
                "consumido",
                "Consumido durante el año",
            ),
            (
                "deteriorado",
                "Deteriorado",
            ),
            (
                "vencido",
                "Vencido",
            ),
            (
                "perdido",
                "Perdido",
            ),
            (
                "otro",
                "Otro motivo",
            ),
        ],
        string="Motivo de ajuste",
        default="no_aplica",
    )

    observacion = fields.Char(
        string="Observación",
    )

    @api.depends(
        "cantidad_sistema",
        "cantidad_a_trasladar",
    )
    def _compute_cantidad_no_aprovechable(
        self
    ):

        for rec in self:

            diferencia = (
                float(
                    rec.cantidad_sistema
                    or
                    0
                )
                -
                float(
                    rec.cantidad_a_trasladar
                    or
                    0
                )
            )

            rec.cantidad_no_aprovechable = (
                diferencia
                if
                diferencia > 0
                else
                0
            )

    @api.depends(
        "cantidad_a_trasladar",
        "cantidad_recibida",
    )
    def _compute_diferencia_ingreso(
        self
    ):

        for rec in self:

            diferencia = (
                float(
                    rec.cantidad_a_trasladar
                    or
                    0
                )
                -
                float(
                    rec.cantidad_recibida
                    or
                    0
                )
            )

            rec.diferencia_ingreso = (
                diferencia
                if
                diferencia > 0
                else
                0
            )

    @api.onchange(
        "cantidad_revisada"
    )
    def _onchange_cantidad_revisada(
        self
    ):

        for rec in self:

            if (
                rec.cierre_id.estado
                ==
                "revision"
            ):

                rec.cantidad_a_trasladar = (
                    rec.cantidad_revisada
                )

    @api.constrains(
        "cantidad_revisada",
        "cantidad_a_trasladar",
        "cantidad_sistema",
        "cantidad_recibida",
    )
    def _check_cantidades(
        self
    ):

        for rec in self:

            if (
                rec.cantidad_revisada
                <
                0
                or
                rec.cantidad_a_trasladar
                <
                0
                or
                rec.cantidad_recibida
                <
                0
            ):

                raise ValidationError(
                    "Las cantidades no "
                    "pueden ser negativas."
                )

            if (
                rec.cantidad_revisada
                >
                rec.cantidad_sistema
            ):

                raise ValidationError(
                    "La cantidad revisada "
                    "no puede ser mayor a "
                    "la cantidad según "
                    "el sistema."
                )

            if (
                rec.cantidad_a_trasladar
                >
                rec.cantidad_revisada
            ):

                raise ValidationError(
                    "La cantidad enviada "
                    "no puede ser mayor a "
                    "la cantidad revisada."
                )

            if (
                rec.cantidad_recibida
                >
                rec.cantidad_a_trasladar
            ):

                raise ValidationError(
                    "La cantidad recibida "
                    "no puede ser mayor a "
                    "la cantidad enviada."
                )


class AnioEscolarCierreUtiles(models.Model):
    _inherit = "anio.escolar"

    cierre_utiles_ids = fields.One2many(
        "cierre.anio.utiles",
        "anio_origen_id",
        string="Cierres de útiles",
    )

    def action_crear_revision_cierre_utiles(
        self
    ):

        self.ensure_one()

        if self.estado != "activo":

            raise UserError(
                "El cierre de útiles solo "
                "puede iniciarse desde el "
                "año escolar activo."
            )

        cierre = self.env[
            "cierre.anio.utiles"
        ].search(
            [
                (
                    "anio_origen_id",
                    "=",
                    self.id,
                ),
            ],
            order="id desc",
            limit=1,
        )

        if not cierre:

            cierre = self.env[
                "cierre.anio.utiles"
            ].create(
                {
                    "anio_origen_id":
                        self.id,
                }
            )

        return (
            cierre
            ._action_abrir_formulario()
        )

    def action_revisar_ingreso_sobrantes(
        self
    ):

        self.ensure_one()

        if self.estado != "activo":

            raise UserError(
                "La revisión de ingreso "
                "solo puede realizarse en "
                "el año escolar activo."
            )

        if not self.anio_anterior_id:

            raise UserError(
                "El año escolar no tiene "
                "un año anterior relacionado."
            )

        cierre = self.env[
            "cierre.anio.utiles"
        ].search(
            [
                (
                    "anio_origen_id",
                    "=",
                    self.anio_anterior_id.id,
                ),
            ],
            order="id desc",
            limit=1,
        )

        if not cierre:

            raise UserError(
                "No se encontró un cierre "
                "de útiles validado para "
                "el año anterior."
            )

        if (
            cierre.estado
            not in
            (
                "cierre_validado",
                "ingreso_revision",
                "confirmado",
            )
        ):

            raise UserError(
                "El cierre de útiles del "
                "año anterior todavía no "
                "ha sido validado."
            )

        if (
            cierre.anio_destino_id
            and
            cierre.anio_destino_id
            !=
            self
        ):

            raise UserError(
                "El cierre de útiles ya "
                "está relacionado con otro "
                "año escolar."
            )

        if (
            cierre.estado
            ==
            "cierre_validado"
        ):

            for linea in cierre.linea_ids:

                linea.write(
                    {
                        "cantidad_recibida":
                            (
                                linea
                                .cantidad_a_trasladar
                            ),
                    }
                )

            cierre.write(
                {
                    "anio_destino_id":
                        self.id,

                    "estado":
                        "ingreso_revision",
                }
            )

        elif (
            not
            cierre.anio_destino_id
        ):

            cierre.write(
                {
                    "anio_destino_id":
                        self.id,
                }
            )

        return (
            cierre
            ._action_abrir_formulario()
        )
from odoo import models, fields, api
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


class CierreAnioUtiles(models.Model):
    _name = "cierre.anio.utiles"
    _description = "Cierre de año y revisión de sobrantes"
    _order = "anio_origen_id desc, id desc"

    name = fields.Char(
        string="Referencia",
        compute="_compute_name",
        store=True
    )

    anio_origen_id = fields.Many2one(
        "anio.escolar",
        string="Año a cerrar",
        required=True,
        readonly=True
    )

    anio_destino_id = fields.Many2one(
        "anio.escolar",
        string="Año destino",
        required=True,
        readonly=True
    )

    fecha_revision = fields.Datetime(
        string="Fecha de revisión",
        default=fields.Datetime.now,
        required=True
    )

    fecha_confirmacion = fields.Datetime(
        string="Fecha de confirmación",
        readonly=True
    )

    responsable_id = fields.Many2one(
        "res.users",
        string="Responsable",
        default=lambda self: self.env.user,
        required=True,
        readonly=True
    )

    estado = fields.Selection(
        [
            ("borrador", "Borrador"),
            ("revision", "En revisión"),
            ("confirmado", "Confirmado"),
        ],
        string="Estado",
        default="borrador",
        required=True
    )

    linea_ids = fields.One2many(
        "cierre.anio.utiles.linea",
        "cierre_id",
        string="Útiles sobrantes revisados"
    )

    total_productos = fields.Integer(
        string="Productos revisados",
        compute="_compute_totales"
    )

    total_sistema = fields.Float(
        string="Cantidad según sistema",
        compute="_compute_totales"
    )

    total_trasladar = fields.Float(
        string="Cantidad a trasladar",
        compute="_compute_totales"
    )

    total_no_aprovechable = fields.Float(
        string="Cantidad no aprovechable",
        compute="_compute_totales"
    )

    observacion = fields.Text(
        string="Observación general"
    )

    @api.depends("anio_origen_id", "anio_destino_id")
    def _compute_name(self):
        for rec in self:
            origen = rec.anio_origen_id.name or ""
            destino = rec.anio_destino_id.name or ""
            rec.name = f"Cierre {origen} → {destino}" if origen and destino else "Cierre de año"

    @api.depends(
        "linea_ids",
        "linea_ids.cantidad_sistema",
        "linea_ids.cantidad_a_trasladar",
        "linea_ids.cantidad_no_aprovechable"
    )
    def _compute_totales(self):
        for rec in self:
            rec.total_productos = len(rec.linea_ids)
            rec.total_sistema = sum(rec.linea_ids.mapped("cantidad_sistema"))
            rec.total_trasladar = sum(rec.linea_ids.mapped("cantidad_a_trasladar"))
            rec.total_no_aprovechable = sum(rec.linea_ids.mapped("cantidad_no_aprovechable"))

    def _fmt_qty(self, value):
        value = float(value or 0)
        if value.is_integer():
            return str(int(value))
        return f"{value:.2f}".rstrip("0").rstrip(".")

    def _calcular_saldos_por_producto_grado(self):
        self.ensure_one()

        Movimiento = self.env["almacen.utiles.movimiento"]

        movimientos = Movimiento.search([
            ("anio_escolar_id", "=", self.anio_origen_id.id),
            ("product_id", "!=", False),
        ])

        saldos = {}

        for mov in movimientos:
            key = (mov.product_id.id, mov.grado_escolar or False)

            if key not in saldos:
                saldos[key] = {
                    "product_id": mov.product_id.id,
                    "grado_escolar": mov.grado_escolar or False,
                    "cantidad": 0.0,
                }

            cantidad = float(mov.cantidad or 0)

            if mov.tipo_movimiento == "entrada":
                saldos[key]["cantidad"] += cantidad
            elif mov.tipo_movimiento == "salida":
                saldos[key]["cantidad"] -= cantidad
            elif mov.tipo_movimiento == "ajuste":
                saldos[key]["cantidad"] += cantidad

        return [
            saldo for saldo in saldos.values()
            if saldo["cantidad"] > 0
        ]

    def action_generar_revision(self):
        for rec in self:
            if rec.estado == "confirmado":
                raise UserError("Este cierre ya fue confirmado y no puede regenerarse.")

            if rec.anio_origen_id.estado == "cerrado":
                raise UserError(
                    "El año escolar ya está cerrado. No se puede volver a generar la revisión."
                )

            saldos = rec._calcular_saldos_por_producto_grado()

            rec.linea_ids.unlink()

            lineas = []

            for saldo in saldos:
                lineas.append((0, 0, {
                    "product_id": saldo["product_id"],
                    "grado_escolar": saldo["grado_escolar"],
                    "cantidad_sistema": saldo["cantidad"],
                    "cantidad_revisada": saldo["cantidad"],
                    "cantidad_a_trasladar": saldo["cantidad"],
                    "motivo_ajuste": "no_aplica",
                }))

            if not lineas:
                raise UserError(
                    "No se encontraron útiles sobrantes para este año escolar. "
                    "Verifica que existan movimientos de entrada y salida en ese periodo."
                )

            rec.write({
                "linea_ids": lineas,
                "estado": "revision",
            })

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Revisión generada",
                "message": "Se generó el reporte de útiles sobrantes para revisión física.",
                "type": "success",
                "sticky": False,
            }
        }

    def action_confirmar_traslado(self):
        Movimiento = self.env["almacen.utiles.movimiento"]
        Sobrante = self.env["sobrante.utiles.anio"]

        for rec in self:
            if rec.estado == "confirmado":
                raise UserError("Este cierre ya fue confirmado.")

            if rec.anio_origen_id.estado == "cerrado":
                raise UserError(
                    "El año escolar ya está cerrado. No se puede confirmar otro traslado."
                )

            if not rec.linea_ids:
                raise UserError("Primero genera la revisión de sobrantes.")

            for linea in rec.linea_ids:
                if linea.cantidad_a_trasladar < 0:
                    raise UserError("La cantidad a trasladar no puede ser negativa.")

                if linea.cantidad_revisada < 0:
                    raise UserError("La cantidad revisada no puede ser negativa.")

                if linea.cantidad_revisada > linea.cantidad_sistema:
                    raise UserError(
                        f"La cantidad revisada no puede ser mayor a la cantidad del sistema para {linea.product_id.display_name}."
                    )

                if linea.cantidad_a_trasladar > linea.cantidad_revisada:
                    raise UserError(
                        f"No puedes trasladar más de lo revisado físicamente para {linea.product_id.display_name}."
                    )

                if linea.cantidad_no_aprovechable > 0 and linea.motivo_ajuste == "no_aplica":
                    raise UserError(
                        f"Selecciona un motivo de ajuste para {linea.product_id.display_name}."
                    )

            for linea in rec.linea_ids:
                producto = linea.product_id
                grado = linea.grado_escolar or False
                cantidad_trasladar = float(linea.cantidad_a_trasladar or 0)
                cantidad_no_aprovechable = float(linea.cantidad_no_aprovechable or 0)

                base_vals = {
                    "product_id": producto.id,
                    "unidad_id": producto.uom_id.id if producto.uom_id else False,
                    "categoria_id": producto.categ_id.id if producto.categ_id else False,
                    "grado_escolar": grado,
                    "responsable_id": self.env.user.id,
                    "anio_origen_id": rec.anio_origen_id.id,
                    "anio_destino_id": rec.anio_destino_id.id,
                }

                if cantidad_no_aprovechable > 0:
                    motivo_label = dict(linea._fields["motivo_ajuste"].selection).get(
                        linea.motivo_ajuste,
                        "Ajuste por cierre de año"
                    )

                    Movimiento.create({
                        **base_vals,
                        "anio_escolar_id": rec.anio_origen_id.id,
                        "tipo_movimiento": "ajuste",
                        "cantidad": -cantidad_no_aprovechable,
                        "destino": "Ajuste de cierre de año",
                        "observacion": (
                            f"Ajuste por cierre de {rec.anio_origen_id.name}. "
                            f"Motivo: {motivo_label}. "
                            f"Cantidad no trasladada: {rec._fmt_qty(cantidad_no_aprovechable)}."
                        ),
                    })

                if cantidad_trasladar > 0:
                    Movimiento.create({
                        **base_vals,
                        "anio_escolar_id": rec.anio_origen_id.id,
                        "tipo_movimiento": "salida",
                        "cantidad": cantidad_trasladar,
                        "destino": rec.anio_destino_id.name,
                        "observacion": (
                            f"Salida de fin de año desde {rec.anio_origen_id.name} "
                            f"para traslado a {rec.anio_destino_id.name}."
                        ),
                    })

                    Movimiento.create({
                        **base_vals,
                        "anio_escolar_id": rec.anio_destino_id.id,
                        "tipo_movimiento": "entrada",
                        "cantidad": cantidad_trasladar,
                        "destino": "Almacén del nuevo periodo",
                        "observacion": (
                            f"Ingreso desde año anterior. "
                            f"Origen: {rec.anio_origen_id.name}. "
                            f"Destino: {rec.anio_destino_id.name}."
                        ),
                    })

                    sobrante = Sobrante.search([
                        ("anio_origen_id", "=", rec.anio_origen_id.id),
                        ("anio_destino_id", "=", rec.anio_destino_id.id),
                        ("product_id", "=", producto.id),
                    ], limit=1)

                    vals_sobrante = {
                        "anio_origen_id": rec.anio_origen_id.id,
                        "anio_destino_id": rec.anio_destino_id.id,
                        "product_id": producto.id,
                        "cantidad_inicial": cantidad_trasladar,
                        "cantidad_usada": 0,
                        "observacion": (
                            f"Sobrante validado en cierre de año. "
                            f"Cantidad según sistema: {rec._fmt_qty(linea.cantidad_sistema)}. "
                            f"Cantidad trasladada: {rec._fmt_qty(cantidad_trasladar)}."
                        ),
                    }

                    if sobrante:
                        sobrante.write(vals_sobrante)
                    else:
                        Sobrante.create(vals_sobrante)

            rec.write({
                "estado": "confirmado",
                "fecha_confirmacion": fields.Datetime.now(),
            })

            rec.anio_origen_id.estado = "cerrado"

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Cierre confirmado",
                "message": "Se registró el ajuste, la salida de fin de año y el ingreso al nuevo periodo.",
                "type": "success",
                "sticky": False,
            }
        }


class CierreAnioUtilesLinea(models.Model):
    _name = "cierre.anio.utiles.linea"
    _description = "Línea de revisión de sobrantes por cierre de año"
    _order = "grado_escolar, product_id"

    cierre_id = fields.Many2one(
        "cierre.anio.utiles",
        string="Cierre de año",
        required=True,
        ondelete="cascade"
    )

    product_id = fields.Many2one(
        "product.product",
        string="Producto",
        required=True,
        readonly=True
    )

    categoria_id = fields.Many2one(
        "product.category",
        string="Categoría",
        related="product_id.categ_id",
        readonly=True
    )

    uom_id = fields.Many2one(
        "uom.uom",
        string="Unidad",
        related="product_id.uom_id",
        readonly=True
    )

    grado_escolar = fields.Selection(
        GRADO_ESCOLAR_SELECTION,
        string="Grado / sección",
        readonly=True
    )

    cantidad_sistema = fields.Float(
        string="Cantidad según sistema",
        readonly=True
    )

    cantidad_revisada = fields.Float(
        string="Cantidad revisada físicamente"
    )

    cantidad_a_trasladar = fields.Float(
        string="Cantidad a trasladar"
    )

    cantidad_no_aprovechable = fields.Float(
        string="No aprovechable / ajuste",
        compute="_compute_cantidad_no_aprovechable",
        store=True
    )

    motivo_ajuste = fields.Selection(
        [
            ("no_aplica", "No aplica"),
            ("consumido", "Consumido durante el año"),
            ("deteriorado", "Deteriorado"),
            ("vencido", "Vencido"),
            ("perdido", "Perdido"),
            ("otro", "Otro motivo"),
        ],
        string="Motivo de ajuste",
        default="no_aplica"
    )

    observacion = fields.Char(
        string="Observación"
    )

    @api.depends("cantidad_sistema", "cantidad_a_trasladar")
    def _compute_cantidad_no_aprovechable(self):
        for rec in self:
            diferencia = float(rec.cantidad_sistema or 0) - float(rec.cantidad_a_trasladar or 0)
            rec.cantidad_no_aprovechable = diferencia if diferencia > 0 else 0

    @api.onchange("cantidad_revisada")
    def _onchange_cantidad_revisada(self):
        for rec in self:
            rec.cantidad_a_trasladar = rec.cantidad_revisada

    @api.constrains("cantidad_revisada", "cantidad_a_trasladar", "cantidad_sistema")
    def _check_cantidades(self):
        for rec in self:
            if rec.cantidad_revisada < 0 or rec.cantidad_a_trasladar < 0:
                raise ValidationError("Las cantidades no pueden ser negativas.")

            if rec.cantidad_revisada > rec.cantidad_sistema:
                raise ValidationError("La cantidad revisada no puede ser mayor a la cantidad según sistema.")

            if rec.cantidad_a_trasladar > rec.cantidad_revisada:
                raise ValidationError("La cantidad a trasladar no puede ser mayor a la cantidad revisada.")


class AnioEscolarCierreUtiles(models.Model):
    _inherit = "anio.escolar"

    cierre_utiles_ids = fields.One2many(
        "cierre.anio.utiles",
        "anio_origen_id",
        string="Cierres de útiles"
    )

    def action_crear_revision_cierre_utiles(self):
        self.ensure_one()

        if self.estado == "cerrado":
            raise UserError("Este año escolar ya está cerrado.")

        anio_destino = self.env["anio.escolar"].search([
            ("anio_anterior_id", "=", self.id)
        ], limit=1)

        if not anio_destino:
            anio_destino = self.env["anio.escolar"].search([
                ("anio", "=", self.anio + 1)
            ], limit=1)

        if not anio_destino:
            raise UserError(
                f"Primero crea el año escolar {self.anio + 1} y selecciona como año anterior {self.name}."
            )

        cierre = self.env["cierre.anio.utiles"].search([
            ("anio_origen_id", "=", self.id),
            ("anio_destino_id", "=", anio_destino.id),
        ], limit=1)

        if not cierre:
            cierre = self.env["cierre.anio.utiles"].create({
                "anio_origen_id": self.id,
                "anio_destino_id": anio_destino.id,
            })

        return {
            "type": "ir.actions.act_window",
            "name": "Cierre de año y revisión de sobrantes",
            "res_model": "cierre.anio.utiles",
            "view_mode": "form",
            "res_id": cierre.id,
            "target": "current",
        }
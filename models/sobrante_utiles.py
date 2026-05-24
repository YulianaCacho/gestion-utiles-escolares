from odoo import models, fields, api
from odoo.exceptions import UserError


class SobranteUtilesAnio(models.Model):
    _name = "sobrante.utiles.anio"
    _description = "Sobrantes de útiles del año anterior"
    _order = "anio_destino_id desc, product_id"

    name = fields.Char(
        string="Referencia",
        compute="_compute_name",
        store=True
    )

    anio_origen_id = fields.Many2one(
        "anio.escolar",
        string="Año origen",
        required=True,
        readonly=True
    )

    anio_destino_id = fields.Many2one(
        "anio.escolar",
        string="Año destino",
        required=True,
        readonly=True
    )

    product_id = fields.Many2one(
        "product.product",
        string="Producto",
        required=True,
        readonly=True
    )

    uom_id = fields.Many2one(
        "uom.uom",
        string="Unidad",
        related="product_id.uom_id",
        readonly=True
    )

    cantidad_inicial = fields.Float(
        string="Sobrante inicial",
        readonly=True
    )

    cantidad_usada = fields.Float(
        string="Cantidad usada",
        default=0.0
    )

    cantidad_disponible = fields.Float(
        string="Disponible",
        compute="_compute_cantidad_disponible",
        store=True
    )

    estado = fields.Selection(
        [
            ("disponible", "Disponible"),
            ("agotado", "Agotado"),
        ],
        string="Estado",
        compute="_compute_estado",
        store=True
    )

    es_anio_actual = fields.Boolean(
        string="Es año actual",
        compute="_compute_es_anio_actual",
        search="_search_es_anio_actual"
    )

    observacion = fields.Text(string="Observación")

    _sql_constraints = [
        (
            "sobrante_unico_por_anio_producto",
            "unique(anio_origen_id, anio_destino_id, product_id)",
            "Ya existe un sobrante para este producto entre esos años escolares."
        )
    ]

    @api.depends("anio_origen_id", "anio_destino_id", "product_id")
    def _compute_name(self):
        for rec in self:
            producto = rec.product_id.display_name or ""
            origen = rec.anio_origen_id.name or ""
            destino = rec.anio_destino_id.name or ""
            rec.name = f"{producto} | {origen} → {destino}"

    @api.depends("cantidad_inicial", "cantidad_usada")
    def _compute_cantidad_disponible(self):
        for rec in self:
            rec.cantidad_disponible = rec.cantidad_inicial - rec.cantidad_usada

    @api.depends("cantidad_disponible")
    def _compute_estado(self):
        for rec in self:
            rec.estado = "disponible" if rec.cantidad_disponible > 0 else "agotado"

    def _compute_es_anio_actual(self):
        anio_actual = self.env.user.anio_escolar_actual_id

        for rec in self:
            rec.es_anio_actual = bool(
                anio_actual and rec.anio_destino_id.id == anio_actual.id
            )

    def _search_es_anio_actual(self, operator, value):
        anio_actual = self.env.user.anio_escolar_actual_id

        if not anio_actual:
            return [("id", "=", 0)]

        if operator in ("=", "==") and value:
            return [("anio_destino_id", "=", anio_actual.id)]

        if operator in ("!=", "<>") and value:
            return [("anio_destino_id", "!=", anio_actual.id)]

        return [("anio_destino_id", "=", anio_actual.id)]


class AnioEscolarSobrantes(models.Model):
    _inherit = "anio.escolar"

    sobrante_ids = fields.One2many(
        "sobrante.utiles.anio",
        "anio_destino_id",
        string="Sobrantes recibidos"
    )

    total_sobrantes = fields.Integer(
        string="Total sobrantes",
        compute="_compute_total_sobrantes"
    )

    @api.depends("sobrante_ids")
    def _compute_total_sobrantes(self):
        for rec in self:
            rec.total_sobrantes = len(rec.sobrante_ids)

    def action_generar_sobrantes_desde_anio_anterior(self):
        Movimiento = self.env["almacen.utiles.movimiento"]
        Sobrante = self.env["sobrante.utiles.anio"]

        total_creados = 0
        total_actualizados = 0

        for rec in self:
            if not rec.anio_anterior_id:
                raise UserError("Primero debes seleccionar el año anterior.")

            productos = Movimiento.search([
                ("anio_escolar_id", "=", rec.anio_anterior_id.id),
                ("product_id", "!=", False),
            ]).mapped("product_id")

            for producto in productos:
                movimientos = Movimiento.search([
                    ("anio_escolar_id", "=", rec.anio_anterior_id.id),
                    ("product_id", "=", producto.id),
                ])

                entradas = sum(
                    movimientos.filtered(
                        lambda m: m.tipo_movimiento == "entrada"
                    ).mapped("cantidad")
                )

                salidas = sum(
                    movimientos.filtered(
                        lambda m: m.tipo_movimiento == "salida"
                    ).mapped("cantidad")
                )

                ajustes = sum(
                    movimientos.filtered(
                        lambda m: m.tipo_movimiento == "ajuste"
                    ).mapped("cantidad")
                )

                cantidad_sobrante = entradas - salidas + ajustes

                if cantidad_sobrante <= 0:
                    continue

                sobrante_existente = Sobrante.search([
                    ("anio_origen_id", "=", rec.anio_anterior_id.id),
                    ("anio_destino_id", "=", rec.id),
                    ("product_id", "=", producto.id),
                ], limit=1)

                if sobrante_existente:
                    sobrante_existente.write({
                        "cantidad_inicial": cantidad_sobrante,
                    })
                    total_actualizados += 1
                else:
                    Sobrante.create({
                        "anio_origen_id": rec.anio_anterior_id.id,
                        "anio_destino_id": rec.id,
                        "product_id": producto.id,
                        "cantidad_inicial": cantidad_sobrante,
                        "cantidad_usada": 0,
                    })
                    total_creados += 1

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Sobrantes generados",
                "message": (
                    f"Sobrantes creados: {total_creados}. "
                    f"Sobrantes actualizados: {total_actualizados}."
                ),
                "type": "success",
                "sticky": False,
            }
        }
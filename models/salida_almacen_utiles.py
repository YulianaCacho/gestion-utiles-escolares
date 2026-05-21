from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError


class SalidaAlmacenUtiles(models.Model):
    _name = "salida.almacen.utiles"
    _description = "Entrega de útiles desde almacén"
    _order = "fecha_salida desc, id desc"

    name = fields.Char(
        string="Código de entrega",
        default="Nueva",
        readonly=True,
        copy=False
    )

    fecha_salida = fields.Datetime(
        string="Fecha y hora de entrega",
        default=fields.Datetime.now,
        required=True
    )

    responsable_id = fields.Many2one(
        "res.partner",
        string="Quién entrega",
        required=True,
        domain="[('cargo_institucional', 'in', ['promotora', 'directora', 'secretaria', 'coordinadora'])]"
    )

    miss_id = fields.Many2one(
        "res.partner",
        string="Miss / docente que recibe",
        required=True
    )

    grado_escolar = fields.Selection([
        ("inicial_3", "Inicial 3 años"),
        ("inicial_4", "Inicial 4 años"),
        ("inicial_5", "Inicial 5 años"),
        ("1er_grado", "1er grado"),
        ("2do_grado", "2do grado"),
        ("3er_grado", "3er grado"),
        ("4to_grado", "4to grado"),
        ("5to_grado", "5to grado"),
        ("6to_grado", "6to grado"),
    ], string="Grado escolar", required=True)

    linea_ids = fields.One2many(
        "salida.almacen.utiles.linea",
        "salida_id",
        string="Productos entregados"
    )

    total_productos = fields.Integer(
        string="Total de productos",
        compute="_compute_totales",
        store=True
    )

    total_cantidad = fields.Float(
        string="Cantidad total entregada",
        compute="_compute_totales",
        store=True
    )

    estado = fields.Selection([
        ("borrador", "Borrador"),
        ("validado", "Validado"),
    ], string="Estado", default="borrador")

    user_id = fields.Many2one(
        "res.users",
        string="Usuario que registró",
        default=lambda self: self.env.user,
        readonly=True
    )

    observacion = fields.Text(string="Observación")

    @api.depends("linea_ids", "linea_ids.cantidad")
    def _compute_totales(self):
        for rec in self:
            rec.total_productos = len(rec.linea_ids)
            rec.total_cantidad = sum(rec.linea_ids.mapped("cantidad"))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "Nueva") == "Nueva":
                vals["name"] = self.env["ir.sequence"].next_by_code("salida.almacen.utiles") or "Nueva"
        return super().create(vals_list)

    def _stock_disponible_producto(self, product_id):
        movimientos = self.env["almacen.utiles.movimiento"].search([
            ("product_id", "=", product_id.id)
        ])

        entradas = sum(movimientos.filtered(lambda m: m.tipo_movimiento == "entrada").mapped("cantidad"))
        salidas = sum(movimientos.filtered(lambda m: m.tipo_movimiento == "salida").mapped("cantidad"))

        return entradas - salidas

    def action_validar_salida(self):
        for rec in self:
            if rec.estado == "validado":
                raise UserError("Esta entrega ya fue validada.")

            if not rec.linea_ids:
                raise UserError("Debes agregar al menos un producto para registrar la entrega.")

            for linea in rec.linea_ids:
                if linea.cantidad <= 0:
                    raise ValidationError("La cantidad entregada debe ser mayor a 0.")

                stock_disponible = rec._stock_disponible_producto(linea.product_id)

                if linea.cantidad > stock_disponible:
                    raise UserError(
                        f"No hay stock suficiente para {linea.product_id.display_name}. "
                        f"Disponible: {stock_disponible}, solicitado: {linea.cantidad}."
                    )

            grado_texto = dict(rec._fields["grado_escolar"].selection).get(
                rec.grado_escolar,
                rec.grado_escolar
            )

            for linea in rec.linea_ids:
                self.env["almacen.utiles.movimiento"].create({
                    "tipo_movimiento": "salida",
                    "salida_almacen_id": rec.id,
                    "product_id": linea.product_id.id,
                    "cantidad": linea.cantidad,
                    "unidad_id": linea.unidad_id.id if linea.unidad_id else False,
                    "categoria_id": linea.categoria_id.id if linea.categoria_id else False,
                    "responsable_id": self.env.user.id,
                    "destino": f"{rec.miss_id.name} - {grado_texto}",
                    "observacion": f"Entrega registrada en {rec.name}. Entrega: {rec.responsable_id.name}. Recibe: {rec.miss_id.name}.",
                })

            rec.estado = "validado"


class SalidaAlmacenUtilesLinea(models.Model):
    _name = "salida.almacen.utiles.linea"
    _description = "Detalle de entrega de útiles desde almacén"

    salida_id = fields.Many2one(
        "salida.almacen.utiles",
        string="Entrega",
        required=True,
        ondelete="cascade"
    )

    product_id = fields.Many2one(
        "product.product",
        string="Producto",
        required=True
    )

    cantidad = fields.Float(
        string="Cantidad entregada",
        required=True,
        default=1
    )

    unidad_id = fields.Many2one(
        "uom.uom",
        string="Unidad",
        related="product_id.uom_id",
        readonly=True
    )

    categoria_id = fields.Many2one(
        "product.category",
        string="Categoría",
        related="product_id.categ_id",
        readonly=True
    )

    stock_disponible = fields.Float(
        string="Stock disponible",
        compute="_compute_stock_disponible"
    )

    observacion = fields.Char(string="Observación")

    @api.depends("product_id")
    def _compute_stock_disponible(self):
        Movimiento = self.env["almacen.utiles.movimiento"]

        for rec in self:
            if not rec.product_id:
                rec.stock_disponible = 0
                continue

            movimientos = Movimiento.search([
                ("product_id", "=", rec.product_id.id)
            ])

            entradas = sum(movimientos.filtered(lambda m: m.tipo_movimiento == "entrada").mapped("cantidad"))
            salidas = sum(movimientos.filtered(lambda m: m.tipo_movimiento == "salida").mapped("cantidad"))

            rec.stock_disponible = entradas - salidas

    @api.constrains("cantidad")
    def _check_cantidad(self):
        for rec in self:
            if rec.cantidad <= 0:
                raise ValidationError("La cantidad entregada debe ser mayor a 0.")


class AlmacenUtilesMovimiento(models.Model):
    _inherit = "almacen.utiles.movimiento"

    salida_almacen_id = fields.Many2one(
        "salida.almacen.utiles",
        string="Entrega relacionada",
        ondelete="cascade"
    )
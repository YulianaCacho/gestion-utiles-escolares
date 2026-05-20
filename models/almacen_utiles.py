from odoo import models, fields, api


class AlmacenUtilesMovimiento(models.Model):
    _name = "almacen.utiles.movimiento"
    _description = "Movimiento de almacén de útiles"
    _order = "fecha desc, id desc"

    name = fields.Char(
        string="Referencia",
        compute="_compute_name",
        store=True
    )

    fecha = fields.Datetime(
        string="Fecha y hora",
        default=fields.Datetime.now,
        required=True
    )

    tipo_movimiento = fields.Selection(
        [
            ("entrada", "Entrada a almacén"),
            ("salida", "Salida de almacén"),
        ],
        string="Tipo de movimiento",
        default="entrada",
        required=True
    )

    recepcion_id = fields.Many2one(
        "recepcion.utiles.escolar",
        string="Recepción relacionada",
        ondelete="cascade"
    )

    matricula_id = fields.Many2one(
        "matricula.escolar",
        string="Matrícula",
        related="recepcion_id.matricula_id",
        store=True,
        readonly=True
    )

    estudiante_id = fields.Many2one(
        "res.partner",
        string="Estudiante",
        related="recepcion_id.estudiante_id",
        store=True,
        readonly=True
    )

    grado_escolar = fields.Selection(
        related="recepcion_id.grado_escolar",
        string="Grado escolar",
        store=True,
        readonly=True
    )

    product_id = fields.Many2one(
        "product.product",
        string="Producto",
        required=True
    )

    cantidad = fields.Float(
        string="Cantidad",
        required=True
    )

    unidad_id = fields.Many2one(
        "uom.uom",
        string="Unidad"
    )

    categoria_id = fields.Many2one(
        "product.category",
        string="Categoría"
    )

    responsable_id = fields.Many2one(
        "res.users",
        string="Responsable",
        default=lambda self: self.env.user,
        readonly=True
    )

    destino = fields.Char(
        string="Destino",
        default="Almacén general"
    )

    observacion = fields.Char(string="Observación")

    @api.depends("tipo_movimiento", "product_id", "cantidad")
    def _compute_name(self):
        for rec in self:
            producto = rec.product_id.display_name or "Producto"
            rec.name = f"{rec.tipo_movimiento or ''} - {producto} - {rec.cantidad or 0}"
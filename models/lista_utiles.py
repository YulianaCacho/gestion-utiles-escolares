from odoo import api, models, fields
from odoo.exceptions import ValidationError


class ListaUtilesGrado(models.Model):
    _name = "lista.utiles.grado"
    _description = "Lista de útiles por grado"
    _rec_name = "name"

    name = fields.Char(
        string="Nombre de la lista",
        compute="_compute_name",
        store=True
    )

    anio = fields.Char(
        string="Año escolar",
        default="2026",
        required=True
    )

    grado_escolar = fields.Selection(
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
        string="Grado escolar",
        required=True
    )

    linea_ids = fields.One2many(
        "lista.utiles.grado.linea",
        "lista_id",
        string="Productos esperados"
    )

    cantidad_productos = fields.Integer(
        string="Cantidad de productos",
        compute="_compute_cantidad_productos"
    )

    @api.depends("anio", "grado_escolar")
    def _compute_name(self):
        grados = dict(self._fields["grado_escolar"].selection)
        for record in self:
            grado = grados.get(record.grado_escolar, "")
            if grado and record.anio:
                record.name = f"Lista de útiles {grado} - {record.anio}"
            else:
                record.name = "Lista de útiles"

    @api.depends("linea_ids")
    def _compute_cantidad_productos(self):
        for record in self:
            record.cantidad_productos = len(record.linea_ids)


class ListaUtilesGradoLinea(models.Model):
    _name = "lista.utiles.grado.linea"
    _description = "Detalle de lista de útiles por grado"

    lista_id = fields.Many2one(
        "lista.utiles.grado",
        string="Lista de útiles",
        required=True,
        ondelete="cascade"
    )

    product_id = fields.Many2one(
        "product.template",
        string="Producto",
        required=True
    )

    cantidad_esperada = fields.Float(
        string="Cantidad esperada",
        required=True,
        default=1
    )

    uom_id = fields.Many2one(
        "uom.uom",
        string="Unidad"
    )

    categoria_id = fields.Many2one(
        "product.category",
        string="Categoría",
        related="product_id.categ_id",
        readonly=True
    )

    tipo_uso_escolar = fields.Selection(
    [
        ("personal", "Útil personal"),
        ("material_comun", "Material común del colegio"),
        ("aula", "Material de aula"),
        ("manualidades", "Manualidades"),
        ("aseo", "Material de aseo"),
        ("psicomotricidad", "Psicomotricidad"),
        ("no_inventariable", "No inventariable"),
    ],
    string="Tipo de uso escolar"
)

    observacion = fields.Char(
        string="Observación"
    )

    @api.onchange("product_id")
    def _onchange_product_id(self):
        for record in self:
           if record.product_id:
              record.uom_id = record.product_id.uom_id
              record.tipo_uso_escolar = record.product_id.tipo_uso_escolar
    @api.constrains("cantidad_esperada")
    def _check_cantidad_esperada(self):
        for record in self:
            if record.cantidad_esperada <= 0:
                raise ValidationError("La cantidad esperada debe ser mayor que 0.")
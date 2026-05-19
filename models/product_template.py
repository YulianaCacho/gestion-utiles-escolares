from odoo import api, models, fields
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = "product.template"

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
        string="Tipo de uso escolar",
        help="Clasifica el útil según el tratamiento que tendrá dentro del proceso escolar.",
    )

    responsable_escolar_ids = fields.Many2many(
        "res.users",
        string="Responsables",
        help="Usuarios responsables del control o seguimiento del producto escolar.",
    )

    ubicacion_fisica_id = fields.Many2one(
        "stock.location",
        string="Ubicación física referencial",
        domain="[('usage', '=', 'internal')]",
        help="Ubicación física donde se almacena el producto dentro del colegio.",
    )

    codigo_ubicacion_fisica = fields.Char(
        string="Código de ubicación",
        compute="_compute_codigo_ubicacion_fisica",
        store=True,
    )

    @api.depends("ubicacion_fisica_id")
    def _compute_codigo_ubicacion_fisica(self):
        for producto in self:
            producto.codigo_ubicacion_fisica = (
                producto.ubicacion_fisica_id.name
                if producto.ubicacion_fisica_id
                else ""
            )

    @api.constrains("responsable_escolar_ids")
    def _check_responsable_escolar_ids(self):
        for product in self:
            if len(product.responsable_escolar_ids) > 3:
                raise ValidationError("Solo se pueden seleccionar hasta 3 responsables.")
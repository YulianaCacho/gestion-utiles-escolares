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

    @api.constrains("name", "default_code")
    def _check_producto_duplicado(self):
        ProductProduct = self.env["product.product"].with_context(
            active_test=False
        )

        for product in self:
            nombre = (product.name or "").strip()
            referencia = (product.default_code or "").strip()

            errores = []

            # Validar que el nombre del producto no esté repetido
            if nombre:
                nombre_duplicado = self.with_context(
                    active_test=False
                ).search_count([
                    ("id", "!=", product.id),
                    ("name", "=ilike", nombre),
                ])

                if nombre_duplicado:
                    errores.append(
                        f"Ya existe un producto registrado con el nombre "
                        f"'{nombre}'."
                    )

            # Validar que la referencia interna no esté repetida
            if referencia:
                referencia_duplicada = ProductProduct.search_count([
                    ("product_tmpl_id", "!=", product.id),
                    ("default_code", "=ilike", referencia),
                ])

                if referencia_duplicada:
                    errores.append(
                        f"Ya existe un producto registrado con la referencia "
                        f"interna '{referencia}'."
                    )

            # Impedir el guardado y mostrar las validaciones encontradas
            if errores:
                raise ValidationError(
                    "No se puede guardar el producto:\n\n- "
                    + "\n- ".join(errores)
                    + "\n\nIngrese un nombre y una referencia interna diferentes."
                )


class ProductCategory(models.Model):
    _inherit = "product.category"

    @api.constrains("name")
    def _check_nombre_categoria_duplicado(self):
        for categoria in self:
            nombre = (categoria.name or "").strip()

            if not nombre:
                continue

            categoria_duplicada = self.search(
                [
                    ("id", "!=", categoria.id),
                    ("name", "=ilike", nombre),
                ],
                limit=1,
            )

            if categoria_duplicada:
                raise ValidationError(
                    "No se puede guardar la categoría.\n\n"
                    f"Ya existe una categoría registrada con el nombre "
                    f"'{nombre}'.\n\n"
                    "Ingrese un nombre diferente."
                )

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

    # =========================
    # DASHBOARD MODERNO
    # =========================

    def _dashboard_grado_label(self, grado):
        mapa = {
            "inicial_3": "Inicial 3 años",
            "inicial_4": "Inicial 4 años",
            "inicial_5": "Inicial 5 años",
            "1er_grado": "1er grado",
            "2do_grado": "2do grado",
            "3er_grado": "3er grado",
            "4to_grado": "4to grado",
            "5to_grado": "5to grado",
            "6to_grado": "6to grado",
        }
        return mapa.get(grado, grado or "Sin grado")

    def _dashboard_grado_class(self, grado):
        if grado in ("inicial_3", "inicial_4", "inicial_5"):
            return "grado-inicial"
        if grado in ("1er_grado", "2do_grado"):
            return "grado-verde"
        if grado in ("3er_grado", "4to_grado"):
            return "grado-azul"
        if grado in ("5to_grado", "6to_grado"):
            return "grado-naranja"
        return "grado-default"

    def _dashboard_icon(self, grado):
        if grado in ("inicial_3", "inicial_4", "inicial_5"):
            return "fa-scissors"
        if grado in ("1er_grado", "2do_grado"):
            return "fa-pencil"
        if grado in ("3er_grado", "4to_grado"):
            return "fa-book"
        if grado in ("5to_grado", "6to_grado"):
            return "fa-files-o"
        return "fa-list"

    def _dashboard_anio_label(self, rec):
        if "anio_escolar_id" in rec._fields and rec.anio_escolar_id:
            return str(rec.anio_escolar_id.anio or rec.anio_escolar_id.name or "")
        return str(rec.anio or "")

    @api.model
    def get_lista_utiles_dashboard(self, search=None):
        domain = []
        search = (search or "").strip()
        anio_actual = self.env.user.anio_escolar_actual_id

        if anio_actual:
            if "anio_escolar_id" in self._fields:
                domain.append(("anio_escolar_id", "=", anio_actual.id))
            else:
                domain.append(("anio", "=", str(anio_actual.anio)))

        if search:
            domain += [
                "|", "|",
                ("name", "ilike", search),
                ("grado_escolar", "ilike", search),
                ("anio", "ilike", search),
            ]

        records = self.search(domain)

        orden_grados = {
            "inicial_3": 1,
            "inicial_4": 2,
            "inicial_5": 3,
            "1er_grado": 4,
            "2do_grado": 5,
            "3er_grado": 6,
            "4to_grado": 7,
            "5to_grado": 8,
            "6to_grado": 9,
        }

        records = sorted(
            records,
            key=lambda rec: (
                self._dashboard_anio_label(rec),
                orden_grados.get(rec.grado_escolar, 99),
                rec.name or "",
            )
        )

        total_listas = len(records)
        total_utiles = sum(rec.cantidad_productos for rec in records)
        promedio = round(total_utiles / total_listas) if total_listas else 0

        rows = []
        for rec in records:
            grado_class = self._dashboard_grado_class(rec.grado_escolar)
            rows.append({
                "id": rec.id,
                "name": rec.name or "Lista de útiles",
                "anio": self._dashboard_anio_label(rec),
                "grado": self._dashboard_grado_label(rec.grado_escolar),
                "grado_class": grado_class,
                "icon_class": grado_class,
                "icon": self._dashboard_icon(rec.grado_escolar),
                "cantidad": rec.cantidad_productos,
            })

        anio_label = str(anio_actual.anio) if anio_actual else "todos los años"

        return {
            "titulo": "Lista de útiles por grado",
            "subtitulo": "Año escolar %s · %s listas" % (anio_label, total_listas),
            "stats": {
                "total_listas": total_listas,
                "total_utiles": total_utiles,
                "promedio_grado": promedio,
            },
            "rows": rows,
        }


    
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
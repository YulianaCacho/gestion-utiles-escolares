from datetime import datetime
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
        ("entrada", "Entrada"),
        ("salida", "Salida"),
        ("ajuste", "Ajuste de inventario"),
    ],
    string="Tipo de movimiento",
    default="entrada",
    required=True
)

    motivo_movimiento = fields.Selection(
    [
        ("entrada_padres", "Ingreso por padres de familia"),
        ("entrada_compra", "Ingreso por compra directa"),
        ("entrada_traslado_interno", "Ingreso por traslado interno"),
        ("entrada_traslado_anio", "Ingreso desde año anterior"),
        ("entrada_otro", "Otro ingreso"),

        ("salida_uso", "Salida por uso"),
        ("salida_entrega_estudiante", "Salida por entrega a estudiante"),
        ("salida_traslado_seccion", "Salida por traslado a otra sección"),
        ("salida_fin_anio", "Salida de fin de año"),
        ("salida_otro", "Otra salida"),

        ("ajuste_inventario", "Ajuste de inventario"),
    ],
    string="Motivo",
    default="entrada_padres",
    required=True,
    index=True
)

    anio_escolar_id = fields.Many2one(
        "anio.escolar",
        string="Año escolar",
        default=lambda self: self.env.user.anio_escolar_actual_id,
        index=True
    )
    
    anio_origen_id = fields.Many2one(
        "anio.escolar",
        string="Año origen",
        help="Se usa cuando el movimiento corresponde a un traslado o cierre de año."
    )

    anio_destino_id = fields.Many2one(
        "anio.escolar",
        string="Año destino",
        help="Se usa cuando el movimiento corresponde a un traslado o cierre de año."
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
        GRADO_ESCOLAR_SELECTION,
        string="Grado o sección",
        index=True
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

    @api.depends("tipo_movimiento", "motivo_movimiento", "product_id", "cantidad")
    def _compute_name(self):
        for rec in self:
            producto = rec.product_id.display_name or "Producto"
            motivo = rec._motivo_label(rec.motivo_movimiento)
            rec.name = f"{rec.tipo_movimiento or ''} - {motivo} - {producto} - {rec.cantidad or 0}"

    def _motivo_label(self, motivo):
        selection = dict(self._fields["motivo_movimiento"].selection)
        return selection.get(motivo, motivo or "Sin motivo")

    def _fmt_qty(self, value):
        value = float(value or 0)
        if value.is_integer():
            return str(int(value))
        return f"{value:.2f}".rstrip("0").rstrip(".")

    def _grado_label(self, grado):
        grados = dict(self.env["matricula.escolar"]._fields["grado_escolar"].selection)
        return grados.get(grado, grado or "Sin grado")

    def _fecha_label(self, fecha):
        if not fecha:
            return ""

        fecha_local = fields.Datetime.context_timestamp(self, fecha)
        return fecha_local.strftime("%d/%m · %H:%M")

    def _build_items_text(self, movimientos):
        partes = []

        for mov in movimientos[:4]:
            producto = mov.product_id.display_name or "Producto"
            cantidad = self._fmt_qty(abs(mov.cantidad))
            partes.append(f"{producto} x{cantidad}")

        if len(movimientos) > 4:
            partes.append(f"+{len(movimientos) - 4} productos más")

        return ", ".join(partes)

    def _build_domain_periodo(self, start, end, anio_escolar_id=False):
        domain = [
            ("fecha", ">=", fields.Datetime.to_string(start)),
            ("fecha", "<", fields.Datetime.to_string(end)),
        ]

        if anio_escolar_id:
            domain.append(("anio_escolar_id", "=", int(anio_escolar_id)))
        else:
            domain.append(("id", "=", 0))

        return domain

    @api.model
    def get_reporte_almacen_movimientos(
        self,
        month=None,
        year=None,
        grado=False,
        responsable_id=False,
        product_id=False,
        anio_escolar_id=False
    ):
        today = fields.Date.context_today(self)

        month = int(month or today.month)
        year = int(year or today.year)

        start = datetime(year, month, 1)

        if month == 12:
            end = datetime(year + 1, 1, 1)
        else:
            end = datetime(year, month + 1, 1)

        domain = self._build_domain_periodo(start, end, anio_escolar_id)

        if grado:
            domain.append(("grado_escolar", "=", grado))

        if responsable_id:
            domain.append(("responsable_id", "=", int(responsable_id)))

        if product_id:
            domain.append(("product_id", "=", int(product_id)))

        movimientos = self.search(domain, order="fecha desc, id desc")

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

        ajustes = movimientos.filtered(lambda m: m.tipo_movimiento == "ajuste")
        ajuste_neto = sum(ajustes.mapped("cantidad"))
        balance = entradas - salidas + ajuste_neto

        meses = [
            "",
            "Enero",
            "Febrero",
            "Marzo",
            "Abril",
            "Mayo",
            "Junio",
            "Julio",
            "Agosto",
            "Septiembre",
            "Octubre",
            "Noviembre",
            "Diciembre",
        ]

        def iniciales(nombre):
            partes = (nombre or "").split()
            if not partes:
                return "--"
            return "".join([p[0].upper() for p in partes[:2]])

        def fecha_local(fecha):
            if not fecha:
                return "", ""

            local = fields.Datetime.context_timestamp(self, fecha)
            fecha_txt = local.strftime("%d %b.").replace("Jun.", "jun.").replace("Jul.", "jul.")
            hora_txt = local.strftime("%I:%M %p").lower()
            hora_txt = hora_txt.replace("am", "a. m.").replace("pm", "p. m.")
            return fecha_txt, hora_txt

        def motivo_label(mov):
            if "motivo_movimiento" in self._fields:
                selection = dict(self._fields["motivo_movimiento"].selection)
                motivo = selection.get(mov.motivo_movimiento)
                if motivo:
                    return motivo

            if mov.tipo_movimiento == "entrada" and mov.recepcion_id:
                return "Ingreso por padres de familia"

            if mov.tipo_movimiento == "salida":
                return "Salida de almacén"

            if mov.tipo_movimiento == "ajuste":
                return "Ajuste de inventario"

            return mov.observacion or "Movimiento de almacén"

        eventos = []

        for mov in movimientos:
            fecha_txt, hora_txt = fecha_local(mov.fecha)
            cantidad = float(mov.cantidad or 0)

            if mov.tipo_movimiento == "salida":
                tipo_label = "Salida"
                tipo_class = "salida"
                tipo_icon = "↑"
            elif mov.tipo_movimiento == "ajuste":
                tipo_label = "Ajuste"
                tipo_class = "ajuste"
                tipo_icon = "↕"
            else:
                tipo_label = "Entrada"
                tipo_class = "entrada"
                tipo_icon = "↓"

            grado_value = mov.grado_escolar

            if not grado_value and mov.recepcion_id:
                grado_value = mov.recepcion_id.grado_escolar

            eventos.append({
                "id": mov.id,
                "fecha": fecha_txt,
                "hora": hora_txt,
                "tipo_label": tipo_label,
                "tipo_class": tipo_class,
                "tipo_icon": tipo_icon,
                "motivo": motivo_label(mov),
                "producto": mov.product_id.display_name or "",
                "grado_label": self._grado_label(grado_value),
                "cantidad": f"{abs(cantidad):.2f}",
                "unidad": mov.unidad_id.name or mov.product_id.uom_id.name or "",
                "destino": mov.destino or "Sin destino",
                "responsable": mov.responsable_id.name or "Sin responsable",
                "responsable_iniciales": iniciales(mov.responsable_id.name),
            })

        grados = []
        grado_info = self.fields_get(["grado_escolar"]).get("grado_escolar", {})
        grado_selection = grado_info.get("selection", [])

        for value, label in grado_selection:
            grados.append({
                "value": value,
                "label": label,
            })

        responsables = []

        responsables_domain = self._build_domain_periodo(
            start,
            end,
            anio_escolar_id
        )

        for user in self.search(responsables_domain).mapped("responsable_id"):
            if user:
                responsables.append({
                    "id": user.id,
                    "name": user.name,
                })
                
        productos = []

        productos_domain = self._build_domain_periodo(
            start,
            end,
            anio_escolar_id
        )

        for product in self.search(productos_domain).mapped("product_id"):
            if product:
                productos.append({
                    "id": product.id,
                    "name": product.display_name,
                })

        return {
            "month_label": f"{meses[month]} {year}",
            "month_short": f"{meses[month].upper()} {year}",
            "kpis": {
                "entradas": self._fmt_qty(entradas),
                "salidas": self._fmt_qty(salidas),
                "ajustes": len(ajustes),
                "balance": self._fmt_qty(balance),
            },
            "events": eventos[:80],
            "grados": grados,
            "responsables": responsables,
            "productos": productos,
        }

    @api.model
    def get_linea_tiempo_movimientos(
        self,
        month=False,
        year=False,
        tipo=False,
        search=False,
        grado=False,
        responsable_id=False,
        product_id=False,
        anio_escolar_id=False
    ):
        today = fields.Date.context_today(self)

        month = int(month or today.month)
        year = int(year or today.year)

        start = datetime(year, month, 1)

        if month == 12:
            end = datetime(year + 1, 1, 1)
        else:
            end = datetime(year, month + 1, 1)

        domain = self._build_domain_periodo(start, end, anio_escolar_id)

        if tipo:
            domain.append(("tipo_movimiento", "=", tipo))

        if grado:
            domain.append(("grado_escolar", "=", grado))

        if responsable_id:
            domain.append(("responsable_id", "=", int(responsable_id)))

        if product_id:
            domain.append(("product_id", "=", int(product_id)))

        movimientos = self.search(domain, order="fecha desc, id desc")

        if search:
            texto = search.lower().strip()
            movimientos = movimientos.filtered(
                lambda m:
                    texto in (m.product_id.display_name or "").lower()
                    or texto in (m.responsable_id.name or "").lower()
                    or texto in (m.observacion or "").lower()
                    or texto in (m.destino or "").lower()
                    or texto in (m.estudiante_id.name or "").lower()
            )

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

        ajustes = movimientos.filtered(lambda m: m.tipo_movimiento == "ajuste")
        ajuste_neto = sum(ajustes.mapped("cantidad"))
        balance = entradas - salidas + ajuste_neto

        meses = [
            "",
            "Enero",
            "Febrero",
            "Marzo",
            "Abril",
            "Mayo",
            "Junio",
            "Julio",
            "Agosto",
            "Septiembre",
            "Octubre",
            "Noviembre",
            "Diciembre",
        ]

        def iniciales(nombre):
            partes = (nombre or "").split()
            if not partes:
                return ""
            return "".join([p[0].upper() for p in partes[:2]])

        def fecha_local(fecha):
            if not fecha:
                return "", ""

            local = fields.Datetime.context_timestamp(self, fecha)
            return local.strftime("%d/%m/%Y"), local.strftime("%H:%M")

        def motivo_label(mov):
            if "motivo_movimiento" in self._fields:
                selection = dict(self._fields["motivo_movimiento"].selection)
                motivo = selection.get(mov.motivo_movimiento)
                if motivo:
                    return motivo

            if mov.tipo_movimiento == "entrada" and mov.recepcion_id:
                estudiante = mov.estudiante_id.name or "Estudiante"
                return f"Recep. matrícula — {estudiante}"

            if mov.tipo_movimiento == "salida":
                return mov.destino or mov.observacion or "Entrega docente"

            if mov.tipo_movimiento == "ajuste":
                return mov.observacion or "Ajuste inventario físico"

            return mov.observacion or "Movimiento registrado"

        rows = []

        for mov in movimientos:
            fecha_txt, hora_txt = fecha_local(mov.fecha)

            cantidad = float(mov.cantidad or 0)

            if mov.tipo_movimiento == "salida":
                cantidad_signed = -abs(cantidad)
                cantidad_class = "neg"
                tipo_label = "Salida"
                tipo_class = "salida"
            elif mov.tipo_movimiento == "ajuste":
                cantidad_signed = cantidad
                cantidad_class = "neg" if cantidad < 0 else "pos"
                tipo_label = "Ajuste"
                tipo_class = "ajuste"
            else:
                cantidad_signed = abs(cantidad)
                cantidad_class = "pos"
                tipo_label = "Entrada"
                tipo_class = "entrada"

            if cantidad_signed > 0:
                cantidad_text = f"+{self._fmt_qty(cantidad_signed)}"
            elif cantidad_signed < 0:
                cantidad_text = f"−{self._fmt_qty(abs(cantidad_signed))}"
            else:
                cantidad_text = "0"

            rows.append({
                "id": mov.id,
                "fecha": fecha_txt,
                "hora": hora_txt,
                "tipo": tipo_label,
                "tipo_class": tipo_class,
                "producto": mov.product_id.display_name or "",
                "cantidad": cantidad_text,
                "cantidad_class": cantidad_class,
                "responsable": mov.responsable_id.name or "",
                "responsable_iniciales": iniciales(mov.responsable_id.name),
                "motivo": motivo_label(mov),
            })

        grados = []
        grado_info = self.fields_get(["grado_escolar"]).get("grado_escolar", {})
        for value, label in grado_info.get("selection", []):
            grados.append({
                "value": value,
                "label": label,
            })

        responsables = []
        responsables_domain = self._build_domain_periodo(start, end, anio_escolar_id)

        for user in self.search(responsables_domain).mapped("responsable_id"):
            if user:
                responsables.append({
                    "id": user.id,
                    "name": user.name,
                })

        return {
            "month_label": f"{meses[month]} {year}",
            "month_short": f"{meses[month]} {year}",
            "total": len(rows),
            "rows": rows,
            "grados": grados,
            "responsables": responsables,
            "kpis": {
                "entradas": self._fmt_qty(entradas),
                "salidas": self._fmt_qty(salidas),
                "ajustes": len(ajustes),
                "balance": self._fmt_qty(balance),
            },
        }
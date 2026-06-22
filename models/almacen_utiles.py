from datetime import datetime
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
            ("ajuste", "Ajuste de inventario"),
        ],
        string="Tipo de movimiento",
        default="entrada",
        required=True
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

        grupos = {}

        for mov in movimientos:
            salida = getattr(mov, "salida_almacen_id", False)

            if mov.tipo_movimiento == "entrada" and mov.recepcion_id:
                key = f"entrada-{mov.recepcion_id.id}"
            elif mov.tipo_movimiento == "salida" and salida:
                key = f"salida-{salida.id}"
            else:
                key = f"{mov.tipo_movimiento}-{mov.id}"

            grupos.setdefault(key, self.env["almacen.utiles.movimiento"])
            grupos[key] |= mov

        eventos = []

        for key, movs in grupos.items():
            movs = movs.sorted(key=lambda m: m.fecha or datetime.min, reverse=True)
            primero = movs[0]
            total = sum(movs.mapped("cantidad"))
            items = self._build_items_text(movs)

            responsable = primero.responsable_id.name or "Sin responsable"

            if primero.tipo_movimiento == "entrada":
                recepcion = primero.recepcion_id
                estudiante = (
                    recepcion.estudiante_id.name
                    if recepcion and recepcion.estudiante_id
                    else "Estudiante"
                )
                grado_label = self._grado_label(
                    recepcion.grado_escolar if recepcion else primero.grado_escolar
                )

                avance = recepcion.porcentaje_avance if recepcion else 0

                if avance >= 100:
                    estado = "Lista completa al 100%."
                elif avance > 0:
                    estado = f"Lista incompleta al {self._fmt_qty(avance)}%."
                else:
                    estado = "Recepción registrada."

                detalle = f"{estudiante} ({grado_label}) entregó: {items}. {estado}"

                eventos.append({
                    "id": key,
                    "tipo": "entrada",
                    "titulo": "Entrada — Recepción por matrícula",
                    "badge": f"+{self._fmt_qty(total)} ítems",
                    "badge_class": "o_ram_badge_pos",
                    "fecha": self._fecha_label(primero.fecha),
                    "responsable": responsable,
                    "detalle": detalle,
                })

            elif primero.tipo_movimiento == "salida":
                salida = getattr(primero, "salida_almacen_id", False)

                docente = (
                    salida.miss_id.name
                    if salida and salida.miss_id
                    else primero.destino or "Docente"
                )
                grado_label = self._grado_label(
                    salida.grado_escolar if salida else primero.grado_escolar
                )
                autorizado = (
                    salida.responsable_id.name
                    if salida and salida.responsable_id
                    else responsable
                )

                detalle = f"{docente} retiró: {items} para {grado_label}. Autorizado por {autorizado}."

                eventos.append({
                    "id": key,
                    "tipo": "salida",
                    "titulo": "Salida — Entrega a docente",
                    "badge": f"−{self._fmt_qty(total)} ítems",
                    "badge_class": "o_ram_badge_neg",
                    "fecha": self._fecha_label(primero.fecha),
                    "responsable": responsable,
                    "detalle": detalle,
                })

            else:
                signo = "+" if total > 0 else "−"
                detalle = primero.observacion or f"Ajuste manual de inventario: {items}."

                eventos.append({
                    "id": key,
                    "tipo": "ajuste",
                    "titulo": "Ajuste — Inventario físico",
                    "badge": f"{signo}{self._fmt_qty(abs(total))} ítems",
                    "badge_class": "o_ram_badge_adjust",
                    "fecha": self._fecha_label(primero.fecha),
                    "responsable": responsable,
                    "detalle": detalle,
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

        return {
            "month_label": f"{meses[month]} {year}",
            "month_short": f"{meses[month].upper()} {year}",
            "kpis": {
                "entradas": self._fmt_qty(entradas),
                "salidas": f"−{self._fmt_qty(salidas)}" if salidas else "0",
                "ajustes": len(ajustes),
                "balance": self._fmt_qty(balance),
            },
            "events": eventos[:50],
            "grados": grados,
            "responsables": responsables,
        }

    @api.model
    def get_linea_tiempo_movimientos(
        self,
        month=False,
        year=False,
        tipo=False,
        search=False,
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
                    or texto in (m._grado_label(m.grado_escolar) or "").lower()
                    or texto in (m.recepcion_id.name or "").lower()
            )

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

            motivo = mov.observacion or ""

            if mov.tipo_movimiento == "entrada" and mov.recepcion_id:
                estudiante = mov.estudiante_id.name or "Estudiante"
                motivo = f"Recep. matrícula — {estudiante}"
            elif mov.tipo_movimiento == "salida":
                motivo = mov.destino or mov.observacion or "Entrega docente"
            elif mov.tipo_movimiento == "ajuste":
                motivo = mov.observacion or "Ajuste inventario físico"

            detalle_partes = []

            if mov.estudiante_id:
                detalle_partes.append(f"Estudiante: {mov.estudiante_id.name}")

            grado_label = self._grado_label(mov.grado_escolar)
            if grado_label and grado_label != "Sin grado":
                detalle_partes.append(f"Grado: {grado_label}")

            if mov.destino:
                detalle_partes.append(f"Destino: {mov.destino}")

            if mov.recepcion_id:
                detalle_partes.append(f"Recepción: {mov.recepcion_id.name}")

            anio_origen = mov.anio_origen_id if "anio_origen_id" in mov._fields else False
            anio_destino = mov.anio_destino_id if "anio_destino_id" in mov._fields else False

            anio_origen = mov.anio_origen_id if "anio_origen_id" in mov._fields else False
            anio_destino = mov.anio_destino_id if "anio_destino_id" in mov._fields else False

            if anio_origen or anio_destino:
                origen = anio_origen.name if anio_origen else ""
                destino = anio_destino.name if anio_destino else ""
                detalle_partes.append(f"Año: {origen} → {destino}" if origen or destino else "")
            
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
                "motivo": motivo,
                "motivo_class": tipo_class,
                "grado": grado_label,
                "destino": mov.destino or "",
                "estudiante": mov.estudiante_id.name or "",
                "recepcion": mov.recepcion_id.name or "",
                "observacion": mov.observacion or "",
                "detalle": " · ".join([p for p in detalle_partes if p]),
            })

        return {
            "month_label": f"{meses[month]} {year}",
            "month_short": f"{meses[month]} {year}",
            "total": len(rows),
            "rows": rows,
        }
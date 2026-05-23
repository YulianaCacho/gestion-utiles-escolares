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

    @api.model
    def get_reporte_almacen_movimientos(self, month=None, year=None, grado=False, responsable_id=False):
        today = fields.Date.context_today(self)

        month = int(month or today.month)
        year = int(year or today.year)

        start = datetime(year, month, 1)

        if month == 12:
            end = datetime(year + 1, 1, 1)
        else:
            end = datetime(year, month + 1, 1)

        domain = [
            ("fecha", ">=", fields.Datetime.to_string(start)),
            ("fecha", "<", fields.Datetime.to_string(end)),
        ]
        if grado:
            domain.append(("grado_escolar", "=", grado))

        if responsable_id:
            domain.append(("responsable_id", "=", int(responsable_id)))

        movimientos = self.search(domain, order="fecha desc, id desc")

        entradas = sum(movimientos.filtered(lambda m: m.tipo_movimiento == "entrada").mapped("cantidad"))
        salidas = sum(movimientos.filtered(lambda m: m.tipo_movimiento == "salida").mapped("cantidad"))
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
                estudiante = recepcion.estudiante_id.name if recepcion and recepcion.estudiante_id else "Estudiante"
                grado = self._grado_label(recepcion.grado_escolar if recepcion else primero.grado_escolar)

                avance = recepcion.porcentaje_avance if recepcion else 0
                if avance >= 100:
                    estado = "Lista completa al 100%."
                elif avance > 0:
                    estado = f"Lista incompleta al {self._fmt_qty(avance)}%."
                else:
                    estado = "Recepción registrada."

                detalle = f"{estudiante} ({grado}) entregó: {items}. {estado}"

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

                docente = salida.miss_id.name if salida and salida.miss_id else primero.destino or "Docente"
                grado = self._grado_label(salida.grado_escolar if salida else primero.grado_escolar)
                autorizado = salida.responsable_id.name if salida and salida.responsable_id else responsable

                detalle = f"{docente} retiró: {items} para {grado}. Autorizado por {autorizado}."

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

                grado_field = self._fields.get("grado_escolar")
                grados = []

                if grado_field:
                    for value, label in grado_field.selection:
                        grados.append({
                            "value": value,
                            "label": label,
                      })

                responsables = []
                for user in self.search(domain).mapped("responsable_id"):
                    responsables.append({
                        "id": user.id,
                        "name": user.name,
                 })
                           
        # Opciones para filtro por grado
        grados = []

        grado_info = self.fields_get(["grado_escolar"]).get("grado_escolar", {})
        grado_selection = grado_info.get("selection", [])

        for value, label in grado_selection:
            grados.append({
                "value": value,
                "label": label,
            })

        # Opciones para filtro por responsable
        responsables = []
        responsables_domain = [
            ("fecha", ">=", fields.Datetime.to_string(start)),
            ("fecha", "<", fields.Datetime.to_string(end)),
        ]

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
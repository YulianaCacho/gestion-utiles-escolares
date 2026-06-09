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

    # =========================
    # DASHBOARD MODERNO: SOBRANTES DEL AÑO ANTERIOR
    # =========================

    def _dashboard_estado_label(self, estado):
        mapa = {
            "disponible": "Disponible",
            "agotado": "Agotado",
        }
        return mapa.get(estado, estado or "Sin estado")

    def _dashboard_estado_class(self, estado):
        if estado == "disponible":
            return "estado-disponible"
        if estado == "agotado":
            return "estado-agotado"
        return "estado-default"

    @api.model
    def get_sobrantes_dashboard(self, search=None):
        domain = []
        search = (search or "").strip()
        anio_actual = self.env.user.anio_escolar_actual_id

        if anio_actual:
            domain.append(("anio_destino_id", "=", anio_actual.id))

        if search:
            domain += [
                "|", "|", "|",
                ("product_id.name", "ilike", search),
                ("product_id.default_code", "ilike", search),
                ("anio_origen_id.name", "ilike", search),
                ("anio_destino_id.name", "ilike", search),
            ]

        records = self.search(domain, order="product_id asc")

        total_productos = len(records)
        unidades_disponibles = sum(records.mapped("cantidad_disponible"))
        disponibles = len(records.filtered(lambda r: r.cantidad_disponible > 0))

        anio_origen = ""
        anio_destino = ""

        if anio_actual:
            anio_destino = str(anio_actual.anio or "")
            if anio_actual.anio_anterior_id:
                anio_origen = str(anio_actual.anio_anterior_id.anio or "")

        if not anio_origen and records:
            anio_origen = str(records[0].anio_origen_id.anio or "")
        if not anio_destino and records:
            anio_destino = str(records[0].anio_destino_id.anio or "")

        rows = []

        for rec in records:
            producto = rec.product_id
            codigo = producto.default_code or "SIN-COD"
            nombre = producto.name or producto.display_name or "Producto sin nombre"

            cantidad_inicial = rec.cantidad_inicial or 0
            cantidad_disponible = rec.cantidad_disponible or 0

            if cantidad_inicial > 0:
                disponible_pct = round((cantidad_disponible / cantidad_inicial) * 100)
            else:
                disponible_pct = 0

            disponible_pct = max(0, min(disponible_pct, 100))

            rows.append({
                "id": rec.id,
                "anio_origen": rec.anio_origen_id.name or "",
                "anio_destino": rec.anio_destino_id.name or "",
                "anio_origen_corto": str(rec.anio_origen_id.anio or rec.anio_origen_id.name or ""),
                "anio_destino_corto": str(rec.anio_destino_id.anio or rec.anio_destino_id.name or ""),
                "codigo": codigo,
                "producto": nombre,
                "cantidad_inicial": "%.2f" % rec.cantidad_inicial,
                "cantidad_usada": "%.2f" % rec.cantidad_usada,
                "cantidad_disponible": "%.0f" % rec.cantidad_disponible,
                "disponible_pct": disponible_pct,
                "unidad": rec.uom_id.name or "",
                "estado": self._dashboard_estado_label(rec.estado),
                "estado_class": self._dashboard_estado_class(rec.estado),
            })

        return {
            "titulo": "Sobrantes del año anterior",
            "stats": {
                "total_productos": total_productos,
                "unidades_disponibles": "%.0f" % unidades_disponibles,
                "disponibles": disponibles,
                "anio_destino": "%s → %s" % (anio_origen, anio_destino) if anio_origen and anio_destino else "",
            },
            "rows": rows,
        }

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
        Sobrante = self.env["sobrante.utiles.anio"].with_context(default_estado=False)
        Producto = self.env["product.product"]
        Quant = self.env["stock.quant"].sudo()

        total_creados = 0
        total_actualizados = 0

        for rec in self:
            if not rec.anio_anterior_id:
                raise UserError("Primero debes seleccionar el año anterior.")

            sobrantes_calculados = {}

            # 1. Intentar calcular desde movimientos escolares del año anterior
            movimientos_anio_anterior = Movimiento.search([
                ("anio_escolar_id", "=", rec.anio_anterior_id.id),
                ("product_id", "!=", False),
            ])

            productos_mov = movimientos_anio_anterior.mapped("product_id")

            for producto in productos_mov:
                movimientos_producto = movimientos_anio_anterior.filtered(
                    lambda m: m.product_id.id == producto.id
                )

                entradas = sum(
                    movimientos_producto.filtered(
                        lambda m: m.tipo_movimiento == "entrada"
                    ).mapped("cantidad")
                )

                salidas = sum(
                    movimientos_producto.filtered(
                        lambda m: m.tipo_movimiento == "salida"
                    ).mapped("cantidad")
                )

                ajustes = sum(
                    movimientos_producto.filtered(
                        lambda m: m.tipo_movimiento == "ajuste"
                    ).mapped("cantidad")
                )

                cantidad_sobrante = entradas - salidas + ajustes

                if cantidad_sobrante > 0:
                    sobrantes_calculados[producto.id] = cantidad_sobrante

                # 2. Si no hay movimientos positivos, usar stock interno real de Odoo
                if not sobrantes_calculados:
                    grupos = Quant.read_group(
                        domain=[
                            ("location_id.usage", "=", "internal"),
                            ("product_id", "!=", False),
                            ("quantity", ">", 0),
                        ],
                        fields=["product_id", "quantity:sum"],
                        groupby=["product_id"],
                    )

                    for grupo in grupos:
                        product_data = grupo.get("product_id")
                        cantidad = grupo.get("quantity", 0)

                    if product_data and cantidad > 0:
                        producto_id = product_data[0]
                        sobrantes_calculados[producto_id] = cantidad

                # 3. Crear o actualizar sobrantes
                for producto_id, cantidad_sobrante in sobrantes_calculados.items():
                    producto = Producto.browse(producto_id)

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
                        Sobrante.with_context(default_estado=False).create({
                            "anio_origen_id": rec.anio_anterior_id.id,
                            "anio_destino_id": rec.id,
                            "product_id": producto.id,
                            "cantidad_inicial": cantidad_sobrante,
                            "cantidad_usada": 0,
                            "observacion": "Sobrante generado desde stock interno disponible del año anterior.",
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
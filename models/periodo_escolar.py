from datetime import datetime

from odoo import models, fields, api


class AnioEscolar(models.Model):
    _inherit = "anio.escolar"

    matricula_ids = fields.One2many(
        "matricula.escolar",
        "anio_escolar_id",
        string="Matrículas"
    )

    lista_utiles_ids = fields.One2many(
        "lista.utiles.grado",
        "anio_escolar_id",
        string="Listas de útiles"
    )

    total_matriculas = fields.Integer(
        string="Total de matrículas",
        compute="_compute_resumen_anio"
    )

    total_listas = fields.Integer(
        string="Total de listas",
        compute="_compute_resumen_anio"
    )

    total_movimientos = fields.Integer(
        string="Movimientos",
        compute="_compute_resumen_anio"
    )

    @api.depends("matricula_ids", "lista_utiles_ids")
    def _compute_resumen_anio(self):
        Movimiento = self.env["almacen.utiles.movimiento"]

        for rec in self:
            rec.total_matriculas = len(rec.matricula_ids)
            rec.total_listas = len(rec.lista_utiles_ids)
            rec.total_movimientos = Movimiento.search_count([
                ("anio_escolar_id", "=", rec.id)
            ])

    def action_vincular_datos_existentes(self):
        Matricula = self.env["matricula.escolar"]
        Lista = self.env["lista.utiles.grado"]
        Salida = self.env["salida.almacen.utiles"]
        Movimiento = self.env["almacen.utiles.movimiento"]

        total_matriculas = 0
        total_listas = 0
        total_salidas = 0
        total_movimientos = 0

        for rec in self:
            matriculas = Matricula.search([
                ("anio_escolar", "=", rec.anio),
                ("anio_escolar_id", "=", False),
            ])
            matriculas.write({
                "anio_escolar_id": rec.id,
            })
            total_matriculas += len(matriculas)

            listas = Lista.search([
                ("anio", "=", str(rec.anio)),
                ("anio_escolar_id", "=", False),
            ])
            listas.write({
                "anio_escolar_id": rec.id,
            })
            total_listas += len(listas)

            fecha_inicio = fields.Datetime.to_string(datetime(rec.anio, 1, 1, 0, 0, 0))
            fecha_fin = fields.Datetime.to_string(datetime(rec.anio + 1, 1, 1, 0, 0, 0))

            salidas = Salida.search([
                ("anio_escolar_id", "=", False),
                ("fecha_salida", ">=", fecha_inicio),
                ("fecha_salida", "<", fecha_fin),
            ])
            salidas.write({
                "anio_escolar_id": rec.id,
            })
            total_salidas += len(salidas)

            movimientos = Movimiento.search([
                ("anio_escolar_id", "=", False),
                ("fecha", ">=", fecha_inicio),
                ("fecha", "<", fecha_fin),
            ])
            movimientos.write({
                "anio_escolar_id": rec.id,
            })
            total_movimientos += len(movimientos)

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Datos vinculados",
                "message": (
                    f"Matrículas: {total_matriculas}. "
                    f"Listas: {total_listas}. "
                    f"Salidas: {total_salidas}. "
                    f"Movimientos: {total_movimientos}."
                ),
                "type": "success",
                "sticky": False,
            }
        }


class MatriculaEscolar(models.Model):
    _inherit = "matricula.escolar"

    anio_escolar_id = fields.Many2one(
        "anio.escolar",
        string="Año escolar",
        default=lambda self: self.env.user.anio_escolar_actual_id.id if self.env.user.anio_escolar_actual_id else False
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        anio_actual = self.env.user.anio_escolar_actual_id
        if anio_actual:
            res.setdefault("anio_escolar_id", anio_actual.id)
            res.setdefault("anio_escolar", anio_actual.anio)

        return res

    @api.onchange("anio_escolar_id")
    def _onchange_anio_escolar_id(self):
        for rec in self:
            if rec.anio_escolar_id:
                rec.anio_escolar = rec.anio_escolar_id.anio

    @api.onchange("anio_escolar_id", "grado_escolar")
    def _onchange_lista_por_anio_grado(self):
        for rec in self:
            if not rec.grado_escolar:
                rec.lista_utiles_id = False
                continue

            dominio = [
                ("grado_escolar", "=", rec.grado_escolar),
            ]

            if rec.anio_escolar_id:
                dominio.append(("anio_escolar_id", "=", rec.anio_escolar_id.id))
            elif rec.anio_escolar:
                dominio.append(("anio", "=", str(rec.anio_escolar)))

            lista = self.env["lista.utiles.grado"].search(dominio, limit=1)
            rec.lista_utiles_id = lista.id if lista else False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("anio_escolar_id"):
                anio = self.env["anio.escolar"].browse(vals["anio_escolar_id"])
                vals["anio_escolar"] = anio.anio

        return super().create(vals_list)

    def write(self, vals):
        if vals.get("anio_escolar_id"):
            anio = self.env["anio.escolar"].browse(vals["anio_escolar_id"])
            vals["anio_escolar"] = anio.anio

        return super().write(vals)


class ListaUtilesGrado(models.Model):
    _inherit = "lista.utiles.grado"

    anio_escolar_id = fields.Many2one(
        "anio.escolar",
        string="Año escolar",
        default=lambda self: self.env.user.anio_escolar_actual_id.id if self.env.user.anio_escolar_actual_id else False
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        anio_actual = self.env.user.anio_escolar_actual_id
        if anio_actual:
            res.setdefault("anio_escolar_id", anio_actual.id)
            res.setdefault("anio", str(anio_actual.anio))

        return res

    @api.onchange("anio_escolar_id")
    def _onchange_anio_escolar_id(self):
        for rec in self:
            if rec.anio_escolar_id:
                rec.anio = str(rec.anio_escolar_id.anio)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("anio_escolar_id"):
                anio = self.env["anio.escolar"].browse(vals["anio_escolar_id"])
                vals["anio"] = str(anio.anio)

        return super().create(vals_list)

    def write(self, vals):
        if vals.get("anio_escolar_id"):
            anio = self.env["anio.escolar"].browse(vals["anio_escolar_id"])
            vals["anio"] = str(anio.anio)

        return super().write(vals)


class RecepcionUtilesEscolar(models.Model):
    _inherit = "recepcion.utiles.escolar"

    anio_escolar_id = fields.Many2one(
        "anio.escolar",
        string="Año escolar",
        related="matricula_id.anio_escolar_id",
        store=True,
        readonly=True
    )


class SalidaAlmacenUtiles(models.Model):
    _inherit = "salida.almacen.utiles"

    anio_escolar_id = fields.Many2one(
        "anio.escolar",
        string="Año escolar",
        default=lambda self: self.env.user.anio_escolar_actual_id.id if self.env.user.anio_escolar_actual_id else False
    )

    def _stock_disponible_producto(self, product_id):
        self.ensure_one()

        domain = [
            ("product_id", "=", product_id.id),
        ]

        if self.anio_escolar_id:
            domain.append(("anio_escolar_id", "=", self.anio_escolar_id.id))

        movimientos = self.env["almacen.utiles.movimiento"].search(domain)

        entradas = sum(movimientos.filtered(lambda m: m.tipo_movimiento == "entrada").mapped("cantidad"))
        salidas = sum(movimientos.filtered(lambda m: m.tipo_movimiento == "salida").mapped("cantidad"))
        ajustes = sum(movimientos.filtered(lambda m: m.tipo_movimiento == "ajuste").mapped("cantidad"))

        return entradas - salidas + ajustes


class AlmacenUtilesMovimiento(models.Model):
    _inherit = "almacen.utiles.movimiento"

    anio_escolar_id = fields.Many2one(
        "anio.escolar",
        string="Año escolar",
        default=lambda self: self.env.user.anio_escolar_actual_id.id if self.env.user.anio_escolar_actual_id else False
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("anio_escolar_id"):
                continue

            anio_id = False

            if vals.get("recepcion_id"):
                recepcion = self.env["recepcion.utiles.escolar"].browse(vals["recepcion_id"])
                if recepcion.matricula_id and recepcion.matricula_id.anio_escolar_id:
                    anio_id = recepcion.matricula_id.anio_escolar_id.id

            if not anio_id and vals.get("salida_almacen_id"):
                salida = self.env["salida.almacen.utiles"].browse(vals["salida_almacen_id"])
                if salida.anio_escolar_id:
                    anio_id = salida.anio_escolar_id.id

            if not anio_id and self.env.user.anio_escolar_actual_id:
                anio_id = self.env.user.anio_escolar_actual_id.id

            if anio_id:
                vals["anio_escolar_id"] = anio_id

        return super().create(vals_list)
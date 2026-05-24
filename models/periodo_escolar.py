from datetime import datetime

from odoo import models, fields, api
from odoo.exceptions import UserError


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

    anio_visual = fields.Char(
        string="Año",
        compute="_compute_anio_visual",
        store=True
   )

    @api.depends("anio")
    def _compute_anio_visual(self):
        for rec in self:
            rec.anio_visual = str(rec.anio) if rec.anio else ""

    @api.depends("matricula_ids", "lista_utiles_ids")
    def _compute_resumen_anio(self):
        Movimiento = self.env["almacen.utiles.movimiento"]

        for rec in self:
            rec.total_matriculas = len(rec.matricula_ids)
            rec.total_listas = len(rec.lista_utiles_ids)
            rec.total_movimientos = Movimiento.search_count([
                ("anio_escolar_id", "=", rec.id)
            ])

    def _siguiente_grado(self, grado):
        mapa = {
            "inicial_3": "inicial_4",
            "inicial_4": "inicial_5",
            "inicial_5": "1er_grado",
            "1er_grado": "2do_grado",
            "2do_grado": "3er_grado",
            "3er_grado": "4to_grado",
            "4to_grado": "5to_grado",
            "5to_grado": "6to_grado",
            "6to_grado": "6to_grado",
        }
        return mapa.get(grado, grado)

    def _buscar_lista_utiles_del_anio(self, grado):
        self.ensure_one()

        return self.env["lista.utiles.grado"].search([
            ("anio_escolar_id", "=", self.id),
            ("grado_escolar", "=", grado),
        ], limit=1)

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

    def action_copiar_listas_desde_anio_anterior(self):
        total = 0

        for rec in self:
            if not rec.anio_anterior_id:
                raise UserError("Primero debes seleccionar el año anterior.")

            listas_anteriores = self.env["lista.utiles.grado"].search([
                ("anio_escolar_id", "=", rec.anio_anterior_id.id),
            ])

            for lista in listas_anteriores:
                existe = self.env["lista.utiles.grado"].search_count([
                    ("anio_escolar_id", "=", rec.id),
                    ("grado_escolar", "=", lista.grado_escolar),
                ])

                if existe:
                    continue

                lista.copy({
                    "anio_escolar_id": rec.id,
                    "anio": str(rec.anio),
                })
                total += 1

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Listas copiadas",
                "message": f"Se copiaron {total} listas al nuevo año escolar.",
                "type": "success",
                "sticky": False,
            }
        }

    def action_generar_matriculas_desde_anio_anterior(self):
        Matricula = self.env["matricula.escolar"]

        creadas = 0
        repetidores = 0
        retirados = 0
        omitidas = 0

        for rec in self:
            if not rec.anio_anterior_id:
                raise UserError("Primero debes seleccionar el año anterior.")

            matriculas_anteriores = Matricula.search([
                ("anio_escolar_id", "=", rec.anio_anterior_id.id),
                ("estado", "=", "activo"),
            ])

            for matricula in matriculas_anteriores:
                if matricula.situacion_siguiente_anio == "retirado":
                    retirados += 1
                    continue

                ya_existe = Matricula.search_count([
                    ("anio_escolar_id", "=", rec.id),
                    ("estudiante_id", "=", matricula.estudiante_id.id),
                ])

                if ya_existe:
                    omitidas += 1
                    continue

                if matricula.situacion_siguiente_anio == "repite":
                    nuevo_grado = matricula.grado_escolar
                    repetidores += 1
                else:
                    nuevo_grado = rec._siguiente_grado(matricula.grado_escolar)

                lista = rec._buscar_lista_utiles_del_anio(nuevo_grado)

                nueva = Matricula.create({
                    "estudiante_id": matricula.estudiante_id.id,
                    "anio_escolar_id": rec.id,
                    "anio_escolar": rec.anio,
                    "grado_escolar": nuevo_grado,
                    "lista_utiles_id": lista.id if lista else False,
                    "estado": "activo",
                    "apoderado_principal_id": matricula.apoderado_principal_id.id if matricula.apoderado_principal_id else False,
                    "apoderado_secundario_id": matricula.apoderado_secundario_id.id if matricula.apoderado_secundario_id else False,
                    "matricula_anterior_id": matricula.id,
                    "situacion_siguiente_anio": "promovido",
                })

                matricula.matricula_siguiente_id = nueva.id
                creadas += 1

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Matrículas generadas",
                "message": (
                    f"Creadas: {creadas}. "
                    f"Repetidores: {repetidores}. "
                    f"Retirados: {retirados}. "
                    f"Omitidas: {omitidas}."
                ),
                "type": "success",
                "sticky": False,
            }
        }

    def action_pasar_a_borrador_prueba(self):
        Recepcion = self.env["recepcion.utiles.escolar"]
        Salida = self.env["salida.almacen.utiles"]
        Movimiento = self.env["almacen.utiles.movimiento"]

        for rec in self:
            if rec.estado == "borrador":
               continue

            recepciones = Recepcion.search_count([
                ("anio_escolar_id", "=", rec.id)
            ])

            salidas = Salida.search_count([
                ("anio_escolar_id", "=", rec.id)
            ])

            movimientos = Movimiento.search_count([
                ("anio_escolar_id", "=", rec.id)
            ])

            if recepciones or salidas or movimientos:
                raise UserError(
                    "No puedes pasar este año a borrador porque ya tiene recepciones, "
                    "entregas o movimientos de almacén registrados. "
                    "Esto evita borrar evidencia importante del sistema."
                )

            rec.estado = "borrador"

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Año escolar actualizado",
                "message": "El año escolar fue pasado a borrador. Ahora puedes eliminarlo si era una prueba.",
                "type": "success",
                "sticky": False,
            }
        }

    def action_eliminar_anio_prueba(self):
        self.unlink()

        return {
            "type": "ir.actions.act_window",
            "name": "Años escolares",
            "res_model": "anio.escolar",
            "view_mode": "list,form",
            "target": "current",
        }

    def unlink(self):
        Matricula = self.env["matricula.escolar"]
        Lista = self.env["lista.utiles.grado"]
        Recepcion = self.env["recepcion.utiles.escolar"]
        Salida = self.env["salida.almacen.utiles"]
        Movimiento = self.env["almacen.utiles.movimiento"]
        Sobrante = self.env["sobrante.utiles.anio"]

        for rec in self:
            if rec.estado != "borrador":
                raise UserError(
                    "No puedes eliminar un año escolar activo o cerrado. "
                    "Solo se pueden eliminar años en estado Borrador usados para prueba."
                )

            anios_dependientes = self.search([
                ("anio_anterior_id", "=", rec.id)
            ])

            if anios_dependientes:
                nombres = ", ".join(anios_dependientes.mapped("name"))
                raise UserError(
                    f"No puedes eliminar {rec.name} porque está configurado como año anterior de: {nombres}. "
                    "Primero elimina o modifica esos años."
                )

            recepciones = Recepcion.search_count([
                ("anio_escolar_id", "=", rec.id)
            ])

            salidas = Salida.search_count([
                ("anio_escolar_id", "=", rec.id)
            ])

            movimientos = Movimiento.search_count([
                ("anio_escolar_id", "=", rec.id)
            ])

            if recepciones or salidas or movimientos:
                raise UserError(
                    "No puedes eliminar este año porque tiene recepciones, entregas o movimientos registrados."
                )

            matriculas = Matricula.search([
                ("anio_escolar_id", "=", rec.id)
            ])

            listas = Lista.search([
                ("anio_escolar_id", "=", rec.id)
            ])

            for matricula in matriculas:
                if matricula.matricula_anterior_id:
                    matricula.matricula_anterior_id.write({
                        "matricula_siguiente_id": False
                    })

            matriculas.unlink()

            for lista in listas:
                if lista.linea_ids:
                    lista.linea_ids.unlink()

            listas.unlink()

            sobrantes = Sobrante.search([
                "|",
                ("anio_destino_id", "=", rec.id),
                ("anio_origen_id", "=", rec.id),
            ])

            if sobrantes:
                sobrantes.unlink()

            usuarios = self.env["res.users"].sudo().search([
                ("anio_escolar_actual_id", "=", rec.id)
            ])
            

            nuevo_anio = rec.anio_anterior_id or self.search([
                ("id", "!=", rec.id)
            ], order="anio desc", limit=1)

            usuarios.write({
                "anio_escolar_actual_id": nuevo_anio.id if nuevo_anio else False
            })

        return super().unlink()


class MatriculaEscolar(models.Model):
    _inherit = "matricula.escolar"

    anio_escolar_id = fields.Many2one(
        "anio.escolar",
        string="Año escolar",
        default=lambda self: self.env.user.anio_escolar_actual_id.id if self.env.user.anio_escolar_actual_id else False
    )

    situacion_siguiente_anio = fields.Selection(
        [
            ("promovido", "Promovido al siguiente grado"),
            ("repite", "Repite grado"),
            ("retirado", "Retirado / no continúa"),
        ],
        string="Situación para el siguiente año",
        default="promovido"
    )

    matricula_anterior_id = fields.Many2one(
        "matricula.escolar",
        string="Matrícula anterior",
        readonly=True
    )

    matricula_siguiente_id = fields.Many2one(
        "matricula.escolar",
        string="Matrícula siguiente",
        readonly=True
    )

    es_anio_actual = fields.Boolean(
       string="Es año actual",
       compute="_compute_es_anio_actual",
       search="_search_es_anio_actual"
    )

    def _compute_es_anio_actual(self):
        anio_actual = self.env.user.anio_escolar_actual_id

        for rec in self:
            rec.es_anio_actual = bool(
               anio_actual and rec.anio_escolar_id.id == anio_actual.id
            )

    def _search_es_anio_actual(self, operator, value):
        anio_actual = self.env.user.anio_escolar_actual_id

        if not anio_actual:
           return [("id", "=", 0)]

        if operator in ("=", "==") and value:
           return [("anio_escolar_id", "=", anio_actual.id)]
 
        if operator in ("!=", "<>") and value:
           return [("anio_escolar_id", "!=", anio_actual.id)]

        return [("anio_escolar_id", "=", anio_actual.id)]

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

    @api.onchange("grado_escolar")
    def _onchange_lista_por_anio_grado(self):
        for rec in self:
            if not rec.grado_escolar:
                rec.lista_utiles_id = False
                continue

            anio = rec.anio_escolar_id

            if not anio and self.env.user.anio_escolar_actual_id:
                anio = self.env.user.anio_escolar_actual_id
                rec.anio_escolar_id = anio.id
                rec.anio_escolar = anio.anio

            dominio = [
                ("grado_escolar", "=", rec.grado_escolar),
            ]

            if anio:
                dominio.append(("anio_escolar_id", "=", anio.id))
            elif rec.anio_escolar:
                dominio.append(("anio", "=", str(rec.anio_escolar)))

            lista = self.env["lista.utiles.grado"].search(dominio, limit=1)

            if not lista and anio:
                lista = self.env["lista.utiles.grado"].search([
                    ("grado_escolar", "=", rec.grado_escolar),
                    ("anio", "=", str(anio.anio)),
                ], limit=1)

            rec.lista_utiles_id = lista.id if lista else False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("anio_escolar_id") and self.env.user.anio_escolar_actual_id:
                vals["anio_escolar_id"] = self.env.user.anio_escolar_actual_id.id

            if vals.get("anio_escolar_id"):
                anio = self.env["anio.escolar"].browse(vals["anio_escolar_id"])
                vals["anio_escolar"] = anio.anio

        return super().create(vals_list)

    def write(self, vals):
        if "anio_escolar_id" in vals and vals.get("anio_escolar_id"):
            nuevo_anio = self.env["anio.escolar"].browse(vals["anio_escolar_id"])

            for rec in self:
                if rec.anio_escolar_id and rec.anio_escolar_id.id != nuevo_anio.id:
                    raise UserError(
                        "No puedes cambiar el año escolar de una matrícula ya registrada. "
                        "Para otro periodo, genera o crea una nueva matrícula en el año correspondiente."
                    )

            vals["anio_escolar"] = nuevo_anio.anio

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
            if not vals.get("anio_escolar_id") and self.env.user.anio_escolar_actual_id:
                vals["anio_escolar_id"] = self.env.user.anio_escolar_actual_id.id

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
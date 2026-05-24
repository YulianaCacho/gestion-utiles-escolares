from odoo import models, fields, api
from odoo.exceptions import ValidationError


class AnioEscolar(models.Model):
    _name = "anio.escolar"
    _description = "Año escolar"
    _rec_name = "name"
    _order = "anio desc"

    name = fields.Char(
        string="Nombre",
        compute="_compute_name",
        store=True
    )

    anio = fields.Integer(
        string="Año",
        required=True
    )

    fecha_inicio = fields.Date(
        string="Fecha de inicio"
    )

    fecha_fin = fields.Date(
        string="Fecha de fin"
    )

    estado = fields.Selection(
        [
            ("borrador", "Borrador"),
            ("activo", "Activo"),
            ("cerrado", "Cerrado"),
        ],
        string="Estado",
        default="borrador"
    )

    anio_anterior_id = fields.Many2one(
        "anio.escolar",
        string="Año anterior"
    )

    observacion = fields.Text(
        string="Observación"
    )

    @api.depends("anio")
    def _compute_name(self):
        for rec in self:
            rec.name = f"Año escolar {rec.anio}" if rec.anio else "Año escolar"

    @api.constrains("anio")
    def _check_anio_unico(self):
        for rec in self:
            existe = self.search_count([
                ("anio", "=", rec.anio),
                ("id", "!=", rec.id)
            ])
            if existe:
                raise ValidationError("Ya existe un registro para ese año escolar.")

    def action_activar(self):
        for rec in self:
            self.search([
                ("estado", "=", "activo"),
                ("id", "!=", rec.id)
            ]).write({
                "estado": "cerrado"
            })

            rec.estado = "activo"

    @api.model
    def get_selector_data(self):
        anios = self.search([], order="anio desc")

        anio_actual = self.env.user.anio_escolar_actual_id

        if not anio_actual:
            anio_actual = self.search([("estado", "=", "activo")], limit=1)

        if not anio_actual:
            anio_actual = self.search([], order="anio desc", limit=1)

        if anio_actual and not self.env.user.anio_escolar_actual_id:
            self.env.user.sudo().write({
                "anio_escolar_actual_id": anio_actual.id
            })

        return {
            "current_id": anio_actual.id if anio_actual else False,
            "current_name": anio_actual.name if anio_actual else "Año escolar",
            "anios": [
                {
                    "id": anio.id,
                    "name": anio.name,
                    "anio": anio.anio,
                }
                for anio in anios
            ],
        }

    @api.model
    def cambiar_anio_escolar(self, anio_id):
        anio = self.browse(int(anio_id))

        if not anio.exists():
            return False

        self.env.user.sudo().write({
            "anio_escolar_actual_id": anio.id
        })

        return True


class ResUsers(models.Model):
    _inherit = "res.users"

    anio_escolar_actual_id = fields.Many2one(
        "anio.escolar",
        string="Año escolar actual"
    )
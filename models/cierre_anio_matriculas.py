from odoo import models, fields, api
from odoo.exceptions import UserError

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


class CierreAnioMatriculas(models.Model):
    _name = "cierre.anio.matriculas"
    _description = "Revisión de promoción de alumnos al cierre de año"
    _order = "anio_origen_id desc, id desc"

    name = fields.Char(
        string="Referencia",
        compute="_compute_name",
        store=True
    )

    anio_origen_id = fields.Many2one(
        "anio.escolar",
        string="Año a revisar",
        required=True,
        readonly=True
    )

    anio_destino_id = fields.Many2one(
        "anio.escolar",
        string="Año destino",
        required=True,
        readonly=True
    )

    fecha_revision = fields.Datetime(
        string="Fecha de revisión",
        default=fields.Datetime.now,
        required=True
    )

    fecha_confirmacion = fields.Datetime(
        string="Fecha de confirmación",
        readonly=True
    )

    responsable_id = fields.Many2one(
        "res.users",
        string="Responsable",
        default=lambda self: self.env.user,
        required=True,
        readonly=True
    )

    estado = fields.Selection(
        [
            ("borrador", "Borrador"),
            ("revision", "En revisión"),
            ("confirmado", "Confirmado"),
        ],
        string="Estado",
        default="borrador",
        required=True
    )

    linea_ids = fields.One2many(
        "cierre.anio.matriculas.linea",
        "cierre_id",
        string="Alumnos revisados"
    )

    total_alumnos = fields.Integer(
        string="Total de alumnos",
        compute="_compute_totales"
    )

    total_promovidos = fields.Integer(
        string="Promovidos",
        compute="_compute_totales"
    )

    total_repiten = fields.Integer(
        string="Repiten",
        compute="_compute_totales"
    )

    total_retirados = fields.Integer(
        string="Retirados",
        compute="_compute_totales"
    )

    observacion = fields.Text(
        string="Observación general"
    )

    @api.depends("anio_origen_id", "anio_destino_id")
    def _compute_name(self):
        for rec in self:
            origen = rec.anio_origen_id.name or ""
            destino = rec.anio_destino_id.name or ""
            rec.name = (
                f"Revisión de promoción {origen} → {destino}"
                if origen and destino else "Revisión de promoción"
            )

    @api.depends("linea_ids", "linea_ids.situacion_revisada")
    def _compute_totales(self):
        for rec in self:
            rec.total_alumnos = len(rec.linea_ids)
            rec.total_promovidos = len(
                rec.linea_ids.filtered(lambda l: l.situacion_revisada == "promovido")
            )
            rec.total_repiten = len(
                rec.linea_ids.filtered(lambda l: l.situacion_revisada == "repite")
            )
            rec.total_retirados = len(
                rec.linea_ids.filtered(lambda l: l.situacion_revisada == "retirado")
            )

    def action_generar_revision(self):
        Matricula = self.env["matricula.escolar"]

        for rec in self:
            if rec.estado == "confirmado":
                raise UserError(
                    "Esta revisión ya fue confirmada y no puede regenerarse."
                )

            matriculas = Matricula.search([
                ("anio_escolar_id", "=", rec.anio_origen_id.id),
                ("estado", "=", "activo"),
            ])

            if not matriculas:
                raise UserError(
                    "No se encontraron matrículas activas para este año escolar."
                )

            rec.linea_ids.unlink()

            lineas = []
            for matricula in matriculas:
                lineas.append((0, 0, {
                    "matricula_id": matricula.id,
                    # Si el alumno ya tenía una situación marcada (por ejemplo,
                    # editada antes desde la matrícula misma), se respeta como
                    # punto de partida en vez de resetear todo a "Promovido".
                    "situacion_revisada": matricula.situacion_siguiente_anio or "promovido",
                }))

            rec.write({
                "linea_ids": lineas,
                "estado": "revision",
            })

        return {
            "type": "ir.actions.act_window",
            "name": "Revisión de promoción de alumnos",
            "res_model": "cierre.anio.matriculas",
            "view_mode": "form",
            "res_id": self.id,
            "target": "current",
        }

    def action_confirmar_revision(self):
        for rec in self:
            if rec.estado == "confirmado":
                raise UserError("Esta revisión ya fue confirmada.")

            if not rec.linea_ids:
                raise UserError("Primero genera la lista de alumnos a revisar.")

            for linea in rec.linea_ids:
                linea.matricula_id.with_context(
                    skip_anio_check=True,
                    permitir_estado_finalizado=True
                ).write({
                    "situacion_siguiente_anio": linea.situacion_revisada,
                    "estado": "finalizado",
                })

            rec.write({
                "estado": "confirmado",
                "fecha_confirmacion": fields.Datetime.now(),
            })

        return {
            "type": "ir.actions.act_window",
            "name": "Revisión de promoción de alumnos",
            "res_model": "cierre.anio.matriculas",
            "view_mode": "form",
            "res_id": self.id,
            "target": "current",
        }


class CierreAnioMatriculasLinea(models.Model):
    _name = "cierre.anio.matriculas.linea"
    _description = "Línea de revisión de promoción por alumno"
    _order = "grado_escolar, estudiante_id"

    cierre_id = fields.Many2one(
        "cierre.anio.matriculas",
        string="Revisión de promoción",
        required=True,
        ondelete="cascade"
    )

    matricula_id = fields.Many2one(
        "matricula.escolar",
        string="Matrícula",
        required=True,
        readonly=True
    )

    estudiante_id = fields.Many2one(
        "res.partner",
        string="Estudiante",
        related="matricula_id.estudiante_id",
        readonly=True
    )

    grado_escolar = fields.Selection(
        GRADO_ESCOLAR_SELECTION,
        string="Grado actual",
        related="matricula_id.grado_escolar",
        readonly=True
    )

    situacion_revisada = fields.Selection(
        [
            ("promovido", "Promovido al siguiente grado"),
            ("repite", "Repite grado"),
            ("retirado", "Retirado / no continúa"),
        ],
        string="Situación",
        default="promovido",
        required=True
    )

    grado_siguiente_label = fields.Char(
        string="Grado el próximo año",
        compute="_compute_grado_siguiente_label"
    )

    observacion = fields.Char(
        string="Observación"
    )

    @api.depends("situacion_revisada", "grado_escolar")
    def _compute_grado_siguiente_label(self):
        labels = dict(GRADO_ESCOLAR_SELECTION)

        for rec in self:
            if rec.situacion_revisada == "retirado":
                rec.grado_siguiente_label = "No continúa"
            elif rec.situacion_revisada == "repite":
                rec.grado_siguiente_label = labels.get(rec.grado_escolar, "")
            else:
                anio = rec.cierre_id.anio_origen_id
                siguiente = anio._siguiente_grado(rec.grado_escolar) if anio else rec.grado_escolar
                rec.grado_siguiente_label = labels.get(siguiente, "")
                
    @api.onchange("situacion_revisada")
    def _onchange_situacion_revisada(self):
        labels = dict(GRADO_ESCOLAR_SELECTION)
        for rec in self:
            if rec.situacion_revisada == "retirado":
                rec.grado_siguiente_label = "No continúa"
            elif rec.situacion_revisada == "repite":
                rec.grado_siguiente_label = labels.get(rec.grado_escolar, "")
            else:
                anio = rec.cierre_id.anio_origen_id
                siguiente = anio._siguiente_grado(rec.grado_escolar) if anio else rec.grado_escolar
                rec.grado_siguiente_label = labels.get(siguiente, "")


class AnioEscolarCierreMatriculas(models.Model):
    _inherit = "anio.escolar"

    cierre_matriculas_ids = fields.One2many(
        "cierre.anio.matriculas",
        "anio_origen_id",
        string="Revisiones de promoción"
    )

    def action_crear_revision_matriculas(self):
        self.ensure_one()

        if self.estado == "cerrado":
            raise UserError("Este año escolar ya está cerrado.")

        anio_destino = self.env["anio.escolar"].search([
            ("anio_anterior_id", "=", self.id)
        ], limit=1)

        if not anio_destino:
            anio_destino = self.env["anio.escolar"].search([
                ("anio", "=", self.anio + 1)
            ], limit=1)

        if not anio_destino:
            raise UserError(
                f"Primero crea el año escolar {self.anio + 1} y selecciona como año anterior {self.name}."
            )

        cierre = self.env["cierre.anio.matriculas"].search([
            ("anio_origen_id", "=", self.id),
            ("anio_destino_id", "=", anio_destino.id),
        ], limit=1)

        if not cierre:
            cierre = self.env["cierre.anio.matriculas"].create({
                "anio_origen_id": self.id,
                "anio_destino_id": anio_destino.id,
            })

        return {
            "type": "ir.actions.act_window",
            "name": "Revisión de promoción de alumnos",
            "res_model": "cierre.anio.matriculas",
            "view_mode": "form",
            "res_id": cierre.id,
            "target": "current",
        }
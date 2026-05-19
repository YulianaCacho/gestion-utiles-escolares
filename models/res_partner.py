from odoo import api, models, fields
from odoo.exceptions import ValidationError

class ResPartner(models.Model):
    _inherit = "res.partner"

    dni_escolar = fields.Char(
        string="DNI",
        size=8
    )


    tipo_contacto_escolar = fields.Selection(
        [
            ("estudiante", "Estudiante"),
            ("apoderado", "Apoderado"),
            ("personal", "Personal de la institución"),
            ("institucion", "Institución educativa")
        ],
        string="Tipo de contacto escolar"
    )

    cargo_institucional = fields.Selection(
    [
        ("ninguno", "Ninguno"),
        ("promotora", "Promotora"),
        ("directora", "Directora"),
        ("secretaria", "Secretaria"),
        ("coordinadora", "Coordinadora"),
        ("auxiliar_recepcion", "Auxiliar de recepción"),
        ("docente", "Docente"),
        ("otro", "Otro"),
    ],
    string="Cargo institucional",
    default="ninguno"
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
            ("6to_grado", "6to grado")
        ],
        string="Grado escolar"
    )

    apoderado_principal_id = fields.Many2one(
        "res.partner",
        string="Apoderado principal",
        domain="[('tipo_contacto_escolar', '=', 'apoderado')]"
    )

    apoderado_secundario_id = fields.Many2one(
        "res.partner",
        string="Apoderado secundario",
        domain="[('tipo_contacto_escolar', '=', 'apoderado')]"
    )

    estudiante_principal_ids = fields.One2many(
        "res.partner",
        "apoderado_principal_id",
        string="Estudiantes relacionados como apoderado principal"
    )

    estudiante_secundario_ids = fields.One2many(
        "res.partner",
        "apoderado_secundario_id",
        string="Estudiantes relacionados como apoderado secundario"
    )

    cantidad_estudiantes_relacionados = fields.Integer(
        string="Cantidad de estudiantes relacionados",
        compute="_compute_cantidad_estudiantes_relacionados",
        store=False
    )

    @api.depends("estudiante_principal_ids", "estudiante_secundario_ids")
    def _compute_cantidad_estudiantes_relacionados(self):
        for partner in self:
            estudiantes = partner.estudiante_principal_ids | partner.estudiante_secundario_ids
            partner.cantidad_estudiantes_relacionados = len(estudiantes)

    @api.constrains("dni_escolar")
    def _check_dni_escolar(self):
       for partner in self:
            if partner.dni_escolar:
                if not partner.dni_escolar.isdigit() or len(partner.dni_escolar) != 8:
                   raise ValidationError("El DNI debe contener exactamente 8 números.")
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class AnioEscolar(models.Model):

    _name = "anio.escolar"
    _description = "Año escolar"
    _rec_name = "name"
    _order = "anio desc"


    # ========================================================
    # CAMPOS
    # ========================================================

    name = fields.Char(
        string="Nombre",
        compute="_compute_name",
        store=True,
    )

    anio = fields.Integer(
        string="Año",
        required=True,
    )

    fecha_inicio = fields.Date(
        string="Fecha de inicio",
    )

    fecha_fin = fields.Date(
        string="Fecha de fin",
    )

    estado = fields.Selection(
        [
            ("borrador", "Borrador"),
            ("activo", "Activo"),
            ("cerrado", "Cerrado"),
        ],
        string="Estado",
        default="borrador",
        required=True,
        copy=False,
    )

    anio_anterior_id = fields.Many2one(
        "anio.escolar",
        string="Año anterior",
        readonly=True,
        copy=False,
        ondelete="restrict",
    )

    observacion = fields.Text(
        string="Observación",
    )


    # ========================================================
    # NOMBRE
    # ========================================================

    @api.depends("anio")
    def _compute_name(self):

        for rec in self:

            rec.name = (
                f"Año escolar {rec.anio}"
                if rec.anio
                else
                "Año escolar"
            )


    # ========================================================
    # CREACIÓN DEL SIGUIENTE AÑO
    # ========================================================

    @api.model_create_multi
    def create(self, vals_list):

        registros = self.browse()

        for vals in vals_list:

            nuevo_anio = int(
                vals.get("anio")
                or
                0
            )

            if not nuevo_anio:

                raise ValidationError(
                    "Debe ingresar un año escolar válido."
                )


            ultimo_anio = self.search(
                [],
                order="anio desc",
                limit=1,
            )


            if ultimo_anio:

                if ultimo_anio.estado != "cerrado":

                    raise UserError(
                        "No se puede crear un nuevo año "
                        "escolar mientras exista un año "
                        "pendiente de cierre."
                        "\n\n"
                        f"Año pendiente: {ultimo_anio.name}"
                        "\n"
                        f"Estado actual: "
                        f"{dict(ultimo_anio._fields['estado'].selection).get(ultimo_anio.estado)}"
                        "\n\n"
                        "Primero complete y valide el "
                        "cierre del año actual."
                    )


                siguiente_anio = (
                    ultimo_anio.anio
                    +
                    1
                )


                if nuevo_anio != siguiente_anio:

                    raise ValidationError(
                        "Los años escolares deben "
                        "crearse de manera consecutiva."
                        "\n\n"
                        f"Último año registrado: "
                        f"{ultimo_anio.anio}"
                        "\n"
                        f"Siguiente año permitido: "
                        f"{siguiente_anio}"
                    )


                vals[
                    "anio_anterior_id"
                ] = ultimo_anio.id


            else:

                vals[
                    "anio_anterior_id"
                ] = False


            if (
                vals.get(
                    "estado",
                    "borrador",
                )
                ==
                "activo"
            ):

                otro_activo = self.search(
                    [
                        (
                            "estado",
                            "=",
                            "activo",
                        ),
                    ],
                    limit=1,
                )

                if otro_activo:

                    raise ValidationError(
                        "No pueden existir dos años "
                        "escolares activos."
                        "\n\n"
                        f"El año activo actual es: "
                        f"{otro_activo.name}"
                    )


            registro = super(
                AnioEscolar,
                self,
            ).create(
                [vals]
            )

            registros |= registro


        return registros


    # ========================================================
    # RESTRICCIONES
    # ========================================================

    @api.constrains("anio")
    def _check_anio_unico(self):

        for rec in self:

            existe = self.search_count(
                [
                    (
                        "anio",
                        "=",
                        rec.anio,
                    ),
                    (
                        "id",
                        "!=",
                        rec.id,
                    ),
                ]
            )

            if existe:

                raise ValidationError(
                    f"Ya existe un registro para "
                    f"el año escolar {rec.anio}."
                )


    @api.constrains("estado")
    def _check_un_solo_anio_activo(self):

        activos = self.search_count(
            [
                (
                    "estado",
                    "=",
                    "activo",
                ),
            ]
        )

        if activos > 1:

            raise ValidationError(
                "No pueden existir varios "
                "años escolares activos."
                "\n\n"
                "Solo un año puede permanecer "
                "en estado Activo."
            )


    @api.constrains(
        "anio_anterior_id",
        "anio",
    )
    def _check_anio_anterior(self):

        for rec in self:

            if not rec.anio_anterior_id:

                continue


            if (
                rec.anio_anterior_id.id
                ==
                rec.id
            ):

                raise ValidationError(
                    "Un año escolar no puede "
                    "ser su propio año anterior."
                )


            if (
                rec.anio_anterior_id.anio
                >=
                rec.anio
            ):

                raise ValidationError(
                    "El año anterior debe ser "
                    "menor que el año actual."
                )


            if (
                rec.anio
                !=
                rec.anio_anterior_id.anio
                +
                1
            ):

                raise ValidationError(
                    "El año anterior debe ser "
                    "inmediatamente anterior."
                    "\n\n"
                    f"Año actual: {rec.anio}"
                    "\n"
                    f"Año anterior: "
                    f"{rec.anio_anterior_id.anio}"
                )


    # ========================================================
    # ACTIVAR AÑO
    # ========================================================

    def action_activar(self):

        for rec in self:

            if rec.estado == "activo":

                continue


            if rec.estado == "cerrado":

                raise UserError(
                    "No se puede reactivar un "
                    "año escolar cerrado."
                    "\n\n"
                    "Los datos históricos deben "
                    "mantenerse sin modificaciones."
                )


            otro_activo = self.search(
                [
                    (
                        "estado",
                        "=",
                        "activo",
                    ),
                    (
                        "id",
                        "!=",
                        rec.id,
                    ),
                ],
                limit=1,
            )


            if otro_activo:

                raise UserError(
                    "No se puede activar este "
                    "año escolar."
                    "\n\n"
                    f"Actualmente está activo: "
                    f"{otro_activo.name}"
                    "\n\n"
                    "Primero debe completar y "
                    "validar el cierre del año "
                    "escolar activo."
                )


            if rec.anio_anterior_id:

                if (
                    rec.anio_anterior_id.estado
                    !=
                    "cerrado"
                ):

                    raise UserError(
                        "No se puede activar el "
                        "nuevo año escolar."
                        "\n\n"
                        f"El año anterior "
                        f"{rec.anio_anterior_id.name} "
                        "todavía no se encuentra "
                        "cerrado."
                    )


            else:

                anio_anterior = self.search(
                    [
                        (
                            "anio",
                            "<",
                            rec.anio,
                        ),
                    ],
                    order="anio desc",
                    limit=1,
                )


                if anio_anterior:

                    if (
                        anio_anterior.estado
                        !=
                        "cerrado"
                    ):

                        raise UserError(
                            "No se puede activar el "
                            "nuevo año."
                            "\n\n"
                            f"Primero debe cerrar "
                            f"{anio_anterior.name}."
                        )


                    rec.anio_anterior_id = (
                        anio_anterior.id
                    )


            rec.estado = "activo"


            # Al activar el nuevo año, los usuarios
            # internos quedan posicionados en ese año.
            usuarios = self.env[
                "res.users"
            ].sudo().search(
                [
                    (
                        "share",
                        "=",
                        False,
                    ),
                ]
            )


            usuarios.write(
                {
                    "anio_escolar_actual_id":
                        rec.id,
                }
            )


        return {
            "type":
                "ir.actions.client",

            "tag":
                "display_notification",

            "params": {

                "title":
                    "Año escolar activado",

                "message":
                    (
                        "El año escolar fue "
                        "activado correctamente. "
                        "Ahora es el único año "
                        "activo del sistema."
                    ),

                "type":
                    "success",

                "sticky":
                    False,
            },
        }


    # ========================================================
    # SELECTOR DE AÑO
    # ========================================================

    @api.model
    def get_selector_data(self):

        anios = self.search(
            [],
            order="anio desc",
        )


        anio_actual = (
            self.env.user
            .anio_escolar_actual_id
        )


        if not anio_actual:

            anio_actual = self.search(
                [
                    (
                        "estado",
                        "=",
                        "activo",
                    ),
                ],
                limit=1,
            )


        if not anio_actual:

            anio_actual = self.search(
                [],
                order="anio desc",
                limit=1,
            )


        if (
            anio_actual
            and
            not
            self.env.user
            .anio_escolar_actual_id
        ):

            self.env.user.sudo().write(
                {
                    "anio_escolar_actual_id":
                        anio_actual.id,
                }
            )


        return {

            "current_id":
                (
                    anio_actual.id
                    if
                    anio_actual
                    else
                    False
                ),

            "current_name":
                (
                    anio_actual.name
                    if
                    anio_actual
                    else
                    "Año escolar"
                ),

            "anios": [

                {
                    "id":
                        anio.id,

                    "name":
                        anio.name,

                    "anio":
                        anio.anio,

                    "estado":
                        anio.estado,
                }

                for anio in anios
            ],
        }


    @api.model
    def cambiar_anio_escolar(
        self,
        anio_id,
    ):

        anio = self.browse(
            int(
                anio_id
            )
        ).exists()


        if not anio:

            return False


        self.env.user.sudo().write(
            {
                "anio_escolar_actual_id":
                    anio.id,
            }
        )


        return True


# ============================================================
# AÑO ESCOLAR SELECCIONADO POR USUARIO
# ============================================================

class ResUsers(models.Model):

    _inherit = "res.users"


    anio_escolar_actual_id = fields.Many2one(
        "anio.escolar",
        string="Año escolar actual",
        ondelete="set null",
    )
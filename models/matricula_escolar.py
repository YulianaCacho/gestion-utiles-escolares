from odoo import models, fields, api
from odoo.exceptions import ValidationError


class MatriculaEscolar(models.Model):
    _name = 'matricula.escolar'
    _description = 'Matrícula escolar'
    _order = 'anio_escolar desc, estudiante_id'

    name = fields.Char(
        string='Referencia',
        compute='_compute_name',
        store=True
    )

    estudiante_id = fields.Many2one(
        'res.partner',
        string='Estudiante',
        required=True,
        domain="[('tipo_contacto_escolar', '=', 'estudiante')]"
    )

    anio_escolar = fields.Integer(
        string='Año escolar',
        required=True,
        default=2026
    )

    anio_escolar_visual = fields.Char(
        string='Año escolar',
        compute='_compute_anio_escolar_visual',
        store=True
    )

    es_anio_actual = fields.Boolean(
        string='Es año actual',
        compute='_compute_es_anio_actual',
        search='_search_es_anio_actual'
    )

    grado_escolar = fields.Selection([
        ('inicial_3', 'Inicial 3 años'),
        ('inicial_4', 'Inicial 4 años'),
        ('inicial_5', 'Inicial 5 años'),
        ('1er_grado', '1er grado'),
        ('2do_grado', '2do grado'),
        ('3er_grado', '3er grado'),
        ('4to_grado', '4to grado'),
        ('5to_grado', '5to grado'),
        ('6to_grado', '6to grado'),
    ], string='Grado escolar', required=True)

    lista_utiles_id = fields.Many2one(
        'lista.utiles.grado',
        string='Lista de útiles',
        domain="[('grado_escolar', '=', grado_escolar)]"
    )

    apoderado_principal_id = fields.Many2one(
        'res.partner',
        string='Apoderado principal',
        related='estudiante_id.apoderado_principal_id',
        readonly=True
    )

    apoderado_secundario_id = fields.Many2one(
        'res.partner',
        string='Apoderado secundario',
        related='estudiante_id.apoderado_secundario_id',
        readonly=True
    )

    estado = fields.Selection([
        ('activo', 'Activo'),
        ('retirado', 'Retirado'),
        ('finalizado', 'Finalizado'),
    ], string='Estado', default='activo')

    observacion = fields.Text(string='Observación')

    # =========================
    # CAMPOS COMPUTADOS
    # =========================

    @api.depends('estudiante_id', 'anio_escolar', 'grado_escolar')
    def _compute_name(self):
        for rec in self:
            estudiante = rec.estudiante_id.name or ''
            grado = dict(rec._fields['grado_escolar'].selection).get(
                rec.grado_escolar,
                ''
            )
            anio = rec.anio_escolar or ''
            rec.name = f'{estudiante} - {grado} - {anio}'

    @api.depends('anio_escolar')
    def _compute_anio_escolar_visual(self):
        for rec in self:
            rec.anio_escolar_visual = str(rec.anio_escolar or '')

    @api.depends('anio_escolar')
    def _compute_es_anio_actual(self):
        anio_actual = self.env.user.anio_escolar_actual_id

        for rec in self:
            if 'anio_escolar_id' in rec._fields and rec.anio_escolar_id:
                rec.es_anio_actual = bool(
                    anio_actual and rec.anio_escolar_id.id == anio_actual.id
                )
            else:
                rec.es_anio_actual = bool(
                    anio_actual and rec.anio_escolar == anio_actual.anio
                )

    def _search_es_anio_actual(self, operator, value):
        anio_actual = self.env.user.anio_escolar_actual_id

        if not anio_actual:
            return [('id', '=', 0)]

        if 'anio_escolar_id' in self._fields:
            campo = 'anio_escolar_id'
            valor = anio_actual.id
        else:
            campo = 'anio_escolar'
            valor = anio_actual.anio

        if operator in ('=', '==') and value:
            return [(campo, '=', valor)]

        if operator in ('!=', '<>') and value:
            return [(campo, '!=', valor)]

        return [(campo, '=', valor)]

    # =========================
    # ONCHANGE
    # =========================
    
    @api.onchange("estudiante_id")
    def _onchange_estudiante_id_datos_registrados(self):
        for rec in self:
            estudiante = rec.estudiante_id

            if not estudiante:
                continue

            if estudiante.grado_escolar:
                rec.grado_escolar = estudiante.grado_escolar

            if "lista_utiles_id" in estudiante._fields and estudiante.lista_utiles_id:
                rec.lista_utiles_id = estudiante.lista_utiles_id.id
            elif rec.grado_escolar:
                rec._onchange_grado_anio()

    def _sync_datos_estudiante_contacto(self):
        for rec in self:
            estudiante = rec.estudiante_id

            if not estudiante:
                continue

            vals = {}

            if estudiante.tipo_contacto_escolar != "estudiante":
                vals["tipo_contacto_escolar"] = "estudiante"

            if rec.grado_escolar and estudiante.grado_escolar != rec.grado_escolar:
                vals["grado_escolar"] = rec.grado_escolar

            if "lista_utiles_id" in estudiante._fields and rec.lista_utiles_id and estudiante.lista_utiles_id != rec.lista_utiles_id:
                vals["lista_utiles_id"] = rec.lista_utiles_id.id

            if vals:
                estudiante.write(vals)

    @api.onchange('grado_escolar', 'anio_escolar')
    def _onchange_grado_anio(self):
        for rec in self:
            if not rec.grado_escolar or not rec.anio_escolar:
                rec.lista_utiles_id = False
                continue

            dominio = [
                ('grado_escolar', '=', rec.grado_escolar),
            ]

            if 'anio_escolar_id' in rec._fields and rec.anio_escolar_id:
                dominio.append(('anio_escolar_id', '=', rec.anio_escolar_id.id))
                lista = self.env['lista.utiles.grado'].search(dominio, limit=1)

                if lista:
                    rec.lista_utiles_id = lista.id
                    continue

            lista = self.env['lista.utiles.grado'].search([
                ('grado_escolar', '=', rec.grado_escolar),
                ('anio', '=', str(rec.anio_escolar)),
            ], limit=1)

            rec.lista_utiles_id = lista.id if lista else False

    # =========================
    # VALIDACIONES
    # =========================

    @api.constrains('estudiante_id', 'anio_escolar')
    def _check_matricula_unica_por_anio(self):
        for rec in self:
            existe = self.search_count([
                ('estudiante_id', '=', rec.estudiante_id.id),
                ('anio_escolar', '=', rec.anio_escolar),
                ('id', '!=', rec.id)
            ])

            if existe:
                raise ValidationError(
                    'Este estudiante ya tiene una matrícula registrada para ese año escolar.'
                )

    # =========================
    # DASHBOARD LISTA DE MATRÍCULA
    # =========================

    def _dashboard_iniciales(self, nombre):
        if not nombre:
            return ""

        partes = [p for p in nombre.strip().split() if p]

        if len(partes) == 1:
            return partes[0][:2].upper()

        return (partes[0][:1] + partes[1][:1]).upper()

    def _dashboard_grado_label(self, grado):
        mapa = {
            "inicial_3": "Inicial 3 años",
            "inicial_4": "Inicial 4 años",
            "inicial_5": "Inicial 5 años",
            "1er_grado": "1er grado",
            "2do_grado": "2do grado",
            "3er_grado": "3er grado",
            "4to_grado": "4to grado",
            "5to_grado": "5to grado",
            "6to_grado": "6to grado",
        }

        return mapa.get(grado, grado or "Sin asignar")

    def _dashboard_grado_class(self, grado):
        label = (self._dashboard_grado_label(grado) or "").lower()

        if "1er" in label:
            return "grado-1"
        if "2do" in label:
            return "grado-2"
        if "3er" in label:
            return "grado-3"
        if "4to" in label:
            return "grado-4"
        if "5to" in label:
            return "grado-5"
        if "6to" in label:
            return "grado-6"

        return "grado-default"

    @api.model
    def get_matriculas_dashboard(self, search=None):
        domain = []
        search = (search or "").strip()
        anio_actual = self.env.user.anio_escolar_actual_id

        if anio_actual:
            if 'anio_escolar_id' in self._fields:
                domain.append(("anio_escolar_id", "=", anio_actual.id))
            else:
                domain.append(("anio_escolar", "=", anio_actual.anio))

        if search:
            domain += [
                "|", "|", "|",
                ("estudiante_id.name", "ilike", search),
                ("grado_escolar", "ilike", search),
                ("apoderado_principal_id.name", "ilike", search),
                ("estado", "ilike", search),
        ]

        records = self.search(domain, order="estudiante_id asc")

        grados = set()
        activos = 0
        rows = []

        for rec in records:
            grado_label = self._dashboard_grado_label(rec.grado_escolar)

            if grado_label and grado_label != "Sin asignar":
                grados.add(grado_label)

            if rec.estado == "activo":
                activos += 1

            rows.append({
                "id": rec.id,
                "iniciales": self._dashboard_iniciales(
                    rec.estudiante_id.name or ""
                ),
                "estudiante": rec.estudiante_id.name or "Sin estudiante",
                "grado": grado_label,
                "grado_class": self._dashboard_grado_class(rec.grado_escolar),
                "apoderado_principal": (
                    rec.apoderado_principal_id.name
                    if rec.apoderado_principal_id
                    else "No registrado"
                ),
                "estado": rec.estado or "activo",
                "estado_label": self._estado_alumno_label_estado(rec.estado),
                "estado_class": self._estado_alumno_class_estado(rec.estado),
            })

        return {
            "titulo": "Lista de matrícula",
            "subtitulo": "Año escolar %s · I.E.P. Genios del Millennium" % (
                anio_actual.anio if anio_actual else ""
            ),
            "stats": {
                "total_estudiantes": len(records),
                "grados_activos": len(grados),
                "matriculas_activas": activos,
            },
            "rows": rows,
        }
        
    # =========================
    # DASHBOARD MODERNO: ESTADO POR ALUMNO
    # =========================

    def _estado_alumno_label_estado(self, estado):
        mapa = {
            "activo": "Activo",
            "retirado": "Retirado",
            "finalizado": "Finalizado",
        }
        return mapa.get(estado, estado or "Sin estado")

    def _estado_alumno_class_estado(self, estado):
        if estado == "activo":
            return "estado-activo"
        if estado == "retirado":
            return "estado-retirado"
        if estado == "finalizado":
            return "estado-finalizado"
        return "estado-finalizado"

    def _estado_alumno_short_situacion(self, situacion):
        mapa = {
            "promovido": "Promovido",
            "repite": "Repite",
            "retirado": "Retirado",
        }
        return mapa.get(situacion, "Promovido")

    def _estado_alumno_class_situacion(self, situacion):
        if situacion == "repite":
            return "situacion-repite"
        if situacion == "retirado":
            return "situacion-retirado"
        return "situacion-promovido"

    def _estado_alumno_color_class(self, index):
        colores = [
            "color-purple",
            "color-green",
            "color-orange",
            "color-pink",
            "color-blue",
            "color-brown",
            "color-lime",
            "color-red",
        ]
        return colores[index % len(colores)]

    @api.model
    def get_estado_alumno_dashboard(self, search=None):
        domain = []
        search = (search or "").strip()
        anio_actual = self.env.user.anio_escolar_actual_id

        if anio_actual:
            if "anio_escolar_id" in self._fields:
                domain.append(("anio_escolar_id", "=", anio_actual.id))
            else:
                domain.append(("anio_escolar", "=", anio_actual.anio))

        if search:
            domain += [
                "|", "|", "|",
                ("estudiante_id.name", "ilike", search),
                ("grado_escolar", "ilike", search),
                ("apoderado_principal_id.name", "ilike", search),
                ("estado", "ilike", search),
            ]

        records = self.search(domain, order="estudiante_id asc")

        rows = []

        for index, rec in enumerate(records):
            situacion = "promovido"

            if "situacion_siguiente_anio" in rec._fields:
                situacion = rec.situacion_siguiente_anio or "promovido"

            apoderado = (
                rec.apoderado_principal_id.name
                if rec.apoderado_principal_id
                else "No registrado"
            )

            rows.append({
                "id": rec.id,
                "iniciales": self._dashboard_iniciales(rec.estudiante_id.name or ""),
                "estudiante": rec.estudiante_id.name or "Sin estudiante",
                "grado": self._dashboard_grado_label(rec.grado_escolar),
                "grado_class": self._dashboard_grado_class(rec.grado_escolar),
                "estado_label": self._estado_alumno_label_estado(rec.estado),
                "estado_class": self._estado_alumno_class_estado(rec.estado),
                "situacion_short": self._estado_alumno_short_situacion(situacion),
                "situacion_class": self._estado_alumno_class_situacion(situacion),
                "apoderado_principal": apoderado,
                "apoderado_iniciales": self._dashboard_iniciales(apoderado),
                "color_class": self._estado_alumno_color_class(index),
            })

        return {
            "rows": rows,
        }
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

    @api.depends('estudiante_id', 'anio_escolar', 'grado_escolar')
    def _compute_name(self):
        for rec in self:
            estudiante = rec.estudiante_id.name or ''
            grado = dict(rec._fields['grado_escolar'].selection).get(rec.grado_escolar, '')
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
            rec.es_anio_actual = bool(
                anio_actual and rec.anio_escolar == anio_actual.anio
            )

    def _search_es_anio_actual(self, operator, value):
        anio_actual = self.env.user.anio_escolar_actual_id

        if not anio_actual:
            return [('id', '=', 0)]

        if operator in ('=', '==') and value:
            return [('anio_escolar', '=', anio_actual.anio)]

        if operator in ('!=', '<>') and value:
            return [('anio_escolar', '!=', anio_actual.anio)]

        return [('anio_escolar', '=', anio_actual.anio)]

    @api.onchange('grado_escolar', 'anio_escolar')
    def _onchange_grado_anio(self):
        for rec in self:
            if not rec.grado_escolar or not rec.anio_escolar:
                rec.lista_utiles_id = False
                continue

            dominio = [
                ('grado_escolar', '=', rec.grado_escolar),
            ]

            # Si existe el campo anio_escolar_id, buscar primero por el año escolar real.
            if hasattr(rec, 'anio_escolar_id') and rec.anio_escolar_id:
                dominio.append(('anio_escolar_id', '=', rec.anio_escolar_id.id))
                lista = self.env['lista.utiles.grado'].search(dominio, limit=1)

                if lista:
                    rec.lista_utiles_id = lista.id
                    continue

            # Si no encuentra por anio_escolar_id, busca por el campo antiguo anio.
            lista = self.env['lista.utiles.grado'].search([
                ('grado_escolar', '=', rec.grado_escolar),
                ('anio', '=', str(rec.anio_escolar)),
            ], limit=1)

            rec.lista_utiles_id = lista.id if lista else False

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
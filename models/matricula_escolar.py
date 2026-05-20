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
        domain="[('anio', '=', anio_escolar), ('grado_escolar', '=', grado_escolar)]"
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

    @api.onchange('grado_escolar', 'anio_escolar')
    def _onchange_grado_anio(self):
        for rec in self:
            if rec.grado_escolar and rec.anio_escolar:
                lista = self.env['lista.utiles.grado'].search([
                    ('grado_escolar', '=', rec.grado_escolar),
                    ('anio', '=', rec.anio_escolar)
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
                raise ValidationError('Este estudiante ya tiene una matrícula registrada para ese año escolar.')
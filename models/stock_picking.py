from odoo import models, fields


class StockPicking(models.Model):
    _inherit = "stock.picking"

    estudiante_id = fields.Many2one(
        "res.partner",
        string="Estudiante",
        domain="[('tipo_contacto_escolar', '=', 'estudiante')]"
    )

    apoderado_entrega_id = fields.Many2one(
        "res.partner",
        string="Apoderado que entrega",
        domain="[('tipo_contacto_escolar', '=', 'apoderado')]"
    )

    estado_entrega_utiles = fields.Selection(
        [
            ("completo", "Completo"),
            ("incompleto", "Incompleto"),
            ("regularizado", "Regularizado"),
            ("observado", "Observado")
        ],
        string="Estado de entrega de útiles"
    )

    tipo_operacion_escolar = fields.Selection(
        [
            ("recepcion_completa", "Recepción completa"),
            ("recepcion_incompleta", "Recepción incompleta"),
            ("regularizacion", "Regularización de faltantes"),
            ("traslado_material_comun", "Traslado de material común"),
            ("devolucion_personal", "Devolución de útiles personales")
        ],
        string="Tipo de operación escolar"
    )

    observacion_faltantes = fields.Text(
        string="Observación de faltantes"
    )

    utiles_personales_verificados = fields.Boolean(
        string="Útiles personales verificados y devueltos"
    )

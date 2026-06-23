from odoo import fields, models


IA_CLASE_SELECTION = [
    ("alcohol_gel", "Alcohol en gel"),
    ("alcohol_liquido", "Alcohol líquido"),
    ("papel_toalla", "Papel toalla"),
    ("panos_humedos", "Paños húmedos"),
    ("goma", "Goma"),
    ("silicona", "Silicona líquida"),
    ("barra_de_silicona", "Barra de silicona"),
    ("lapiceros", "Lapiceros"),
    ("lapiz", "Lápiz"),
    ("lapiz_rojo", "Lápiz rojo"),
    ("corrector", "Corrector"),
    ("resaltador", "Resaltador"),
    ("borrador", "Borrador"),
    ("tajador", "Tajador"),
    ("tijera", "Tijera"),
    ("plumones", "Plumones"),
    ("plumon_de_pizarra", "Plumón de pizarra"),
    ("plumon_indeleble", "Plumón indeleble"),
    ("colores_crayones", "Colores / Crayones"),
    ("plastilina", "Plastilina"),
    ("pintura_acrilica", "Pintura acrílica"),
    ("tempera", "Témpera"),
    ("pincel_lengua", "Pincel lengua de gato"),
    ("tizas_pastel", "Tizas pastel"),
    ("cuaderno", "Cuaderno"),
    ("archivador", "Archivador"),
    ("cartuchera", "Cartuchera"),
    ("regla", "Regla"),
    ("transportador", "Transportador"),
    ("cinta_masking", "Cinta masking"),
]


class ProductTemplateIAUtiles(models.Model):
    _inherit = "product.template"

    ia_clase_util = fields.Selection(
        selection=IA_CLASE_SELECTION,
        string="Clase IA",
        help="Clase del modelo YOLO usada para relacionar este producto con el reconocimiento inteligente.",
    )


class ProductProductIAUtiles(models.Model):
    _inherit = "product.product"

    ia_clase_util = fields.Selection(
        selection=IA_CLASE_SELECTION,
        related="product_tmpl_id.ia_clase_util",
        string="Clase IA",
        readonly=False,
        help="Clase del modelo YOLO usada para relacionar este producto con el reconocimiento inteligente.",
    )
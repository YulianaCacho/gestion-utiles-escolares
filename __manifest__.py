{
    "name": "Gestión de Útiles Escolares",
    "version": "1.1",
    "summary": "Adaptación de Odoo para la gestión de útiles escolares",
    "description": "Campos personalizados para estudiantes, apoderados, productos y recepciones de útiles escolares.",
    "author": "Equipo Taller Integrador I",
    "category": "Inventory",
    "depends": ["base", "contacts", "stock", "product"],
    "data": [
        "views/res_partner_views.xml",
        "views/product_template_views.xml",
        "views/stock_picking_views.xml",
        "views/lista_utiles_views.xml",
        "security/ir.model.access.csv",
        'views/recepcion_utiles_views.xml',
        'reports/reporte_recepcion_utiles.xml',
    ],
   'assets': {
        'web.assets_backend': [
            'gestion_utiles_escolares/static/src/css/backend_theme.css',
        ],
    },
    "installable": True,
    "application": True,
    "license": "LGPL-3"
}

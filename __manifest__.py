{
    "name": "Gestión de Útiles Escolares",
    "version": "1.1",
    "summary": "Adaptación de Odoo para la gestión de útiles escolares",
    "description": "Campos personalizados para estudiantes, apoderados, productos y recepciones de útiles escolares.",
    "author": "Equipo Taller Integrador I",
    "category": "Inventory",
    "depends": ["base", "contacts", "stock", "product"],
    "data": [
    'security/security.xml',
    'security/ir.model.access.csv',
    'data/sequence.xml',

    "views/res_partner_views.xml",
    "views/product_template_views.xml",
    "views/stock_picking_views.xml",

    # Primero se carga almacén porque Recepciones y Entregas dependen de ese menú
    'views/almacen_utiles_views.xml',
    'views/recepcion_utiles_views.xml',

    # Luego Matrículas
    'views/matricula_escolar_views.xml',

    # Luego Lista de útiles porque ahora irá dentro de Matrículas
    "views/lista_utiles_views.xml",

    # Luego Entregas
    'views/salida_almacen_utiles_views.xml',

    'reports/reporte_recepcion_utiles.xml',
    'views/favicon_views.xml',

    "views/dashboard_utiles_views.xml",
    "views/reportes_menu_views.xml",
],
   'assets': {
        'web.assets_backend': [
            'gestion_utiles_escolares/static/src/css/backend_theme.css',
            "gestion_utiles_escolares/static/src/css/dashboard_utiles.css",
            "gestion_utiles_escolares/static/src/js/dashboard_utiles.js",
            "gestion_utiles_escolares/static/src/xml/dashboard_utiles.xml",
        ],
    },
    "installable": True,
    "application": True,
    "license": "LGPL-3"
}

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
    'reports/reporte_linea_tiempo_movimientos.xml',
    'reports/reporte_almacen_movimientos_pdf.xml',
    'views/favicon_views.xml',

    "views/dashboard_utiles_views.xml",
    "views/reportes_menu_views.xml",
    "views/reporte_recepcion_dashboard_views.xml",
    "views/reporte_almacen_movimientos_views.xml",

    'views/anio_escolar_views.xml',
    'views/anio_escolar_views.xml',
    'views/sobrante_utiles_views.xml',
    'views/cierre_anio_utiles_views.xml',
    'views/recepcion_ia_views.xml',
    "views/reconocimiento_ia_views.xml",
    
   
    

],
    'assets': {
        'web.assets_backend': [
            'gestion_utiles_escolares/static/src/css/backend_theme.css',
            "gestion_utiles_escolares/static/src/css/dashboard_utiles.css",
            "gestion_utiles_escolares/static/src/js/dashboard_utiles.js",
            "gestion_utiles_escolares/static/src/xml/dashboard_utiles.xml",

            "gestion_utiles_escolares/static/src/css/reporte_recepcion_dashboard.css",
            "gestion_utiles_escolares/static/src/js/reporte_recepcion_dashboard.js",
            "gestion_utiles_escolares/static/src/xml/reporte_recepcion_dashboard.xml",

            "gestion_utiles_escolares/static/src/css/reporte_almacen_movimientos.css",
            "gestion_utiles_escolares/static/src/js/reporte_almacen_movimientos.js",
            "gestion_utiles_escolares/static/src/xml/reporte_almacen_movimientos.xml",
        
            "gestion_utiles_escolares/static/src/css/reporte_linea_tiempo_movimientos.css",
            "gestion_utiles_escolares/static/src/js/reporte_linea_tiempo_movimientos.js",
            "gestion_utiles_escolares/static/src/xml/reporte_linea_tiempo_movimientos.xml",
        
            "gestion_utiles_escolares/static/src/css/recepcion_almacen_dashboard.css",
            "gestion_utiles_escolares/static/src/js/recepcion_almacen_dashboard.js",
            "gestion_utiles_escolares/static/src/xml/recepcion_almacen_dashboard.xml",
            "gestion_utiles_escolares/static/src/css/recepcion_utiles_form_clean.css",

            "gestion_utiles_escolares/static/src/css/entregas_list_clean.css",
            "gestion_utiles_escolares/static/src/css/anio_escolar_systray.css",
            "gestion_utiles_escolares/static/src/js/anio_escolar_systray.js",
            "gestion_utiles_escolares/static/src/xml/anio_escolar_systray.xml", 

            "gestion_utiles_escolares/static/src/js/matricula_dashboard.js",
            "gestion_utiles_escolares/static/src/xml/matricula_dashboard.xml",
            "gestion_utiles_escolares/static/src/css/matricula_dashboard.css",
            
            "gestion_utiles_escolares/static/src/js/lista_utiles_dashboard.js",
            "gestion_utiles_escolares/static/src/xml/lista_utiles_dashboard.xml",
            "gestion_utiles_escolares/static/src/css/lista_utiles_dashboard.css",
        
            "gestion_utiles_escolares/static/src/js/estado_alumno_dashboard.js",
            "gestion_utiles_escolares/static/src/xml/estado_alumno_dashboard.xml",
            "gestion_utiles_escolares/static/src/css/estado_alumno_dashboard.css",
            
            "gestion_utiles_escolares/static/src/js/sobrantes_dashboard.js",
            "gestion_utiles_escolares/static/src/xml/sobrantes_dashboard.xml",
            "gestion_utiles_escolares/static/src/css/sobrantes_dashboard.css",
        
            'gestion_utiles_escolares/static/src/css/reconocimiento_ia_dashboard.css',
            'gestion_utiles_escolares/static/src/js/reconocimiento_ia_dashboard.js',
            'gestion_utiles_escolares/static/src/xml/reconocimiento_ia_dashboard.xml', 
        
        ],
    },
    "installable": True,
    "application": True,
    "license": "LGPL-3"
}

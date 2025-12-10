{
    'name': 'Tag Sequence Manager',
    'version': '18.0.1.0.4',
    'category': 'Accounting/Analytic',
    'summary': 'Gestor de colecciones, secuencias e informes CSV dinámicos',
    'author': 'Assistant',
    'depends': ['base', 'account', 'analytic'],
    'data': [
        'security/ir.model.access.csv',
        'views/sequence_manager_views.xml',
        'wizard/sequence_report_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
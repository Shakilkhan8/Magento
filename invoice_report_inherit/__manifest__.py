# -*- coding: utf-8 -*-
{
    'name': "invoice_report_inherit",
    'category': 'Uncategorized',
    'version': '16.0.1',

    'depends': ['base', 'sale'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'report/invoice_header.xml',
        'report/invoice_template.xml',
        'views/views.xml',
        'views/templates.xml',
    ],
}

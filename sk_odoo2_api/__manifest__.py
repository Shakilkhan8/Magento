# -*- coding: utf-8 -*-
{
    'name': "SK | Odoo2 API",

    'summary': "This module contain inventory related api to post data to another odoo system",

    'author': "SK Technology",


    # any module necessary for this one to work correctly
    'depends': ['base', 'stock'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
        'views/configuration_view.xml',
    ],
}


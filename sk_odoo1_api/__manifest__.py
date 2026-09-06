# -*- coding: utf-8 -*-
{
    'name': "SK | Odoo1 API",

    'summary': "This module is about to sync SKU number between two Odoo ",

    'description': """
        This module is about to sync SKU number between two Odoo 
    """,

    'author': "SK Technology",
    # any module necessary for this one to work correctly
    'depends': ['base', 'stock', 'sale', 'account', 'contacts', 'website'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/configuration_view.xml',
        'views/templates.xml',
        'views/account_move_view.xml',
        'views/inventory_view.xml',
    ],

}

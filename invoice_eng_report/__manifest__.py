# -*- coding: utf-8 -*-
{
    'name': "Invoice Eng Report",

    'summary': """
        This is all about invoice english report""",

    'description': """
        Long description of module's purpose
    """,

    'author': "SK Technology",
    'website': "https://www.yourcompany.com",


    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'report/invoice_action.xml',
        'report/invoice_template.xml',
        'report/header.xml',
    ],

}

# -*- coding: utf-8 -*-
{
    'name': "Invoice Eng Report",
    'summary': """This is all about invoice english report""",
    'description': """Long description of module's purpose""",
    'author': "SK Technology",
    'website': "https://www.yourcompany.com",
    'category': 'Uncategorized',
    'version': '0.1',
    'depends': ['base', 'sale', 'stock', 'account'],
    'data': [
        # 'security/ir.model.access.csv',
        'report/invoice_action.xml',
        'report/invoice_template.xml',
        'report/header.xml',
        'report/inherit_sale_order_report.xml',
        'report/delivory_report_temp.xml',
        'report/inherit_invoice_report_temp.xml',
        'views/inherit_sale_order_line.xml',
        'views/inherit_customer.xml',
        'views/templates.xml',
    ],

}

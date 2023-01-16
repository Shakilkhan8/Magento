
{
    'name': "EQW Stock Customization ",
    'author': 'Doaa',
    'category': 'ALL',
    'summary': """
    
     """,
    'license': 'AGPL-3',
    'description': """
     
""",
    'version': '1.0',
    'depends': ['base','stock','sale'],
    'data': [
        'views/warehouse_view_inherit.xml',
        'views/stock_picking_type_inherit_view.xml',
        'views/stock_picking_view_inherit.xml',
        'views/sale_order_inherit_view.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}

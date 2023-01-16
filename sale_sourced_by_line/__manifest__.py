
{
    "name": "Sale Sourced by Line",
    "summary": "Multiple warehouse source locations for Sale order",
    "version": "16.0.1.1.0",

    "category": "Warehouse",
    "license": "AGPL-3",
    "depends": ['product','stock',
        "sale_procurement_group_by_line",
    ],
    "data": ["view/sale_view.xml",
             "view/product_template_inherit_view.xml",
             ],
    "installable": True,
}

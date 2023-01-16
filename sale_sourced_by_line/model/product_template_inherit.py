from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    source_warehouse_id = fields.Many2one(
        'stock.warehouse',
        'Source Warehouse',
        help="product warehouse",
    )

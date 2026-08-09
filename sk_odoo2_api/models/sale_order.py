from odoo import api, fields, models

class SaleOrder(models.Model):
    _inherit = "sale.order"

    api_order_id = fields.Integer(
        string="API Order ID"
    )

    courier_name = fields.Char(
        string="Courier Name"
    )

    weight = fields.Float(
        string="Weight"
    )
    shipping_weight = fields.Float(
        string="Shipping Weight"
    )

    carrier_tracking_ref = fields.Char(
        string='Tracking Ref'
    )

    move_type = fields.Selection([
        ('direct', 'As soon as possible'),
        ('one', 'When all products are ready'),
    ], default='direct', string='Shipping Policy')
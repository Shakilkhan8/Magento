from odoo import api, fields, models

class SaleOrder(models.Model):
    _inherit = "sale.order"

    api_order_id = fields.Integer(
        string="API Order ID"
    )
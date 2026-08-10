from odoo import api, fields, models
from odoo.exceptions import ValidationError


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

    def action_confirm(self):
        res = super().action_confirm()
        for rec in self:
            if rec.picking_ids:
                delivery_method = self.env['delivery.carrier'].search([('name', '=', rec.courier_name)], limit=1)
                if delivery_method:
                    for picking in rec.picking_ids:
                        picking.carrier_id = delivery_method.id
                else:
                    raise ValidationError('Need delivery method !')

        return res
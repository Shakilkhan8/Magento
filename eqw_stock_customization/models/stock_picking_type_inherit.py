from odoo import api, fields, models


class StockPickingType(models.Model):
    """
    Describes fields and methods for Magento products
    """
    _inherit = 'stock.picking.type'

    warehouse_type = fields.Selection(selection=[('aramex','Aramex'),('elba','ELBA')],
                                      string='Warehouse Type',related='warehouse_id.warehouse_type',
                                      )

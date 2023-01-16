from odoo import fields,models,api


class WarehouseStock(models.Model):
    """
    Describes fields and methods for Magento products
    """
    _inherit = 'stock.warehouse'

    warehouse_type = fields.Selection(selection=[('aramex','Aramex'),('elba','ELBA')],
                                      string='Warehouse Type',default='aramex',required=1)

    email = fields.Char(string="Email")



from odoo import fields,models,api


class MagentoProductProduct(models.Model):
    """
    Describes fields and methods for Magento products
    """
    _inherit = 'magento.product.product'

    def _prepare_product_values(self, item):
        """
            inherit this  method  to pass value lead time in product form
            from magento to odoo
        """
        values = super(MagentoProductProduct,self)._prepare_product_values(item)
        delivery_day_count = item.get('custom_attributes').get('delivery_day_count')
        values.update({
            'sale_delay': int(delivery_day_count)
        })
        return values


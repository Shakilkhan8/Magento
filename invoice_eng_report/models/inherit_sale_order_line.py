from odoo import models, fields


class InheritSaleOrderModel(models.Model):
    _inherit = 'sale.order'

    # def action_confirm(self):
    #     result = super().action_confirm()
    #     for rec in self.order_line:
    #         rec.invoice_lines.account_price_per_box = rec.sale_price_per_box
    #     return result


class InheritSaleOrderLineModel(models.Model):
    _inherit = 'sale.order.line'

    sale_price_per_box = fields.Char(string='Price Per Box')

    # def _prepare_invoice_line(self, **optional_values):
    #     res = super()._prepare_invoice_line(**optional_values)
    #     res['account_price_per_box'] = self.sale_price_per_box
    #     return res


class InheritStockPickingModel(models.Model):
    _inherit = 'stock.move'

    stock_price_per_box = fields.Char(string='Price Per Box')


class InheritAccountMoveModel(models.Model):
    _inherit = 'account.move.line'

    account_price_per_box = fields.Char(string='Price Per Box')

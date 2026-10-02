from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Source Warehouse",
        help=(
            "If a source warehouse is selected, it will be used "
            "to define the route. Otherwise, the warehouse of "
            "the sale order will be used."
        ),
    )

    @api.onchange("product_id")
    def _onchange_product_id_source_warehouse(self):
        for line in self:
            if line.product_id.source_warehouse_id:
                line.warehouse_id = line.product_id.source_warehouse_id

    def _prepare_procurement_values(self, group_id=False):
        values = super()._prepare_procurement_values(group_id)

        self.ensure_one()

        warehouse = (
            self.warehouse_id
            or self.order_id.warehouse_id
        )

        if warehouse:
            values["warehouse_id"] = warehouse

        return values

    def _get_procurement_group_key(self):
        """
        Keep sale lines separated according to source warehouse.
        """
        priority = 10

        key = super()._get_procurement_group_key()

        if key[0] >= priority:
            return key

        warehouse = (
            self.warehouse_id
            or self.order_id.warehouse_id
        )

        return priority, warehouse.id if warehouse else False
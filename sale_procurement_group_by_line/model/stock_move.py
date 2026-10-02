# Copyright 2022 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _update_candidate_moves_list(self, candidate_moves_list):
        """
        Keep stock moves separated by Sales Order Line.

        Odoo 19 no longer has procurement_group_id on stock moves,
        so use the Sale Order Line / stock reference relationship.
        """

        res = super()._update_candidate_moves_list(
            candidate_moves_list
        )

        if self.env.context.get("sale_group_by_line"):
            for move in self:
                sale_line = move.sale_line_id

                if not sale_line:
                    continue

                # Odoo 19:
                # Get references associated with this SO.
                references = sale_line.order_id.stock_reference_ids

                if references:
                    # Find stock moves connected with the same references.
                    reference_moves = references.mapped("move_ids")

                    if reference_moves:
                        candidate_moves_list.append(
                            reference_moves
                        )

        return res

from odoo import api, fields, models

class AccountMove(models.Model):
    _inherit = 'account.move'


    bill_id = fields.Many2one(
        comodel_name='account.move',
        string='Bill',
    )


    def action_post(self):
        res = super(AccountMove, self).action_post()

        for rec in self:
            if not rec.bill_id:
                lines = []
                partner = rec.partner_id.search([('is_billing_partner', '=', True)], limit=1)
                journal = rec.journal_id.search([('type', '=', 'purchase')], limit=1)
                if rec.invoice_line_ids:
                    lines = [(0,0, {
                        'product_id': line.product_id.id,
                        'quantity': line.extra_delivery_qty,
                        'price_unit': self.get_cost_price(price_val=line.product_id.standard_price, categ_id=line.product_id.categ_id.id),
                        'price_subtotal': line.price_subtotal,
                        'product_uom_id': line.product_uom_id.id if line.product_uom_id else False,
                    }) for line in rec.invoice_line_ids if line.extra_delivery_qty > 0]
                if lines:

                    if partner and journal:
                        bill = rec.create({
                            'partner_id': partner.id,
                            'invoice_date': rec.invoice_date,
                            'invoice_line_ids': lines,
                            'journal_id': journal.id,
                            'move_type': 'in_invoice',
                        })
                        if bill:
                            bill.action_post()
                            rec.bill_id = bill.id
                    else:
                        raise ValidationError("Partner and Purchase Journal are required !")
            else:

                lines = [(0, 0, {
                    'product_id': line.product_id.id,
                    'quantity': line.extra_delivery_qty,
                    'price_unit': self.get_cost_price(price_val=line.product_id.standard_price, categ_id=line.product_id.categ_id.id),
                    'price_subtotal': line.price_subtotal,
                    'product_uom_id': line.product_uom_id.id if line.product_uom_id else False,
                }) for line in rec.invoice_line_ids if line.extra_delivery_qty > 0]
                partner = rec.partner_id.search([('is_billing_partner', '=', True)], limit=1)
                journal = rec.journal_id.search([('type', '=', 'purchase')], limit=1)
                rec.bill_id.invoice_line_ids = [(5,0, rec.bill_id.invoice_line_ids.ids)]
                rec.bill_id.write({
                    'partner_id': partner.id,
                    'journal_id': journal.id,
                    'invoice_date': rec.invoice_date,
                    'invoice_line_ids': lines,
                })
                rec.bill_id.action_post()
        return res

    def get_cost_price(self, price_val = 0.0, categ_id = False):
        percentage = self.env['profit.margin.categories'].search([
            ('category_id', '=', categ_id),
            ('state', '=', 'confirm')
        ], limit=1)

        price = (price_val * percentage.percentage / 100) + price_val

        return price or price_val

    def action_cancel(self):
        res = super(AccountMove, self).action_cancel()
        if self.bill_id:
            self.bill_id.action_cancel()
        return res

    def button_draft(self):
        res = super(AccountMove, self).button_draft()
        if self.bill_id.state == 'posted':
            self.bill_id.button_draft()
        return res



class AccountMoveInherit(models.Model):
    _inherit = 'account.move.line'

    extra_delivery_qty = fields.Float(
        string='Extra Delivery Qty (IMR)',
        help="Quantity that must come from IMR warehouse if other warehouses are short."
    )



class ResPartnerInherit(models.Model):
    _inherit = 'res.partner'

    is_billing_partner = fields.Boolean(
        string='Is Billing Partner',
    )

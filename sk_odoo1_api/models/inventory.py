from odoo import api, fields, models

class ProfitMargin(models.Model):
    _name = 'profit.margin'

    name = fields.Char(
        default = lambda rec: ('New'),
        string='Name',
    )

    description = fields.Char(
        string='Description',
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('closed', 'Closed'),
    ], default='draft',)

    date = fields.Date(
        string='Date',
    )

    line_ids = fields.One2many(
        comodel_name='profit.margin.categories',
        inverse_name='profit_margin_id',
    )


    @api.model
    def create(self, vals):
        res = super(ProfitMargin, self).create(vals)
        sequence = self.env['ir.sequence'].next_by_code('profit.margin.sequence')
        res.name = sequence
        return res


class ProfitMargingCategories(models.Model):
    _name = 'profit.margin.categories'

    category_id = fields.Many2one(
        comodel_name='product.category',
        string='Category',
    )
    percentage = fields.Float(
        string='Percentage',
    )

    profit_margin_id = fields.Many2one(
        comodel_name='profit.margin',
        string='Profit Margin',
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('closed', 'Closed'),
    ], default='draft', related='profit_margin_id.state')


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    is_backorder = fields.Boolean(
        string='Is Extra Backorder',
        default=False,
        help="True if this picking is a backorder created for extra delivery qty"
    )

    backorder_of_id = fields.Many2one(
        'stock.picking',
        string='Backorder Of',
        help="Original picking this backorder was created from"
    )


class StockMovesInherit(models.Model):
    _inherit = 'stock.move'

    extra_delivery_qty = fields.Float(
        string='Extra Delivery Quantity',
        related='sale_line_id.extra_delivery_qty',
        store=True
    )
    aladin_qty = fields.Float(
        string='Aladin Qty',
        related='sale_line_id.aladin_qty',
        store=True
    )


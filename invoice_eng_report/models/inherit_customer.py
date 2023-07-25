from odoo import models, fields


class InheritCustomerModel(models.Model):
    _inherit = 'res.partner'

    customer_code = fields.Char(string='Customer Code')

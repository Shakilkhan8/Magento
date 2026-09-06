from odoo import api, fields, models

class APIConfiguration(models.Model):
    _name = 'api.configuration'


    name = fields.Char(
        string='Name',
        required=True
    )

    url = fields.Char(
        string='URL',
        required=True
    )

    db_name = fields.Char(
        string='DB Name',
        required=True
    )
    user_name = fields.Char(
        string='User Name',
        required=True
    )

    password = fields.Char(
        string='Password',
        required=True
    )



class StoreDeletedSequence(models.Model):
    _name = 'store.deleted.sequence'

    name = fields.Char(
        string='Name',
    )
    is_active = fields.Boolean(
        default=False
    )

    product_tmpl_id = fields.Many2one(
        comodel_name='product.template',
    )

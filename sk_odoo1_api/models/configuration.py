from odoo import api, fields, models

class APIConfiguration(models.Model):
    _name = 'api.configuration'


    name = fields.Char(
        string='Name',
    )

    url = fields.Char(
        string='URL',
    )

    db_name = fields.Char(
        string='DB Name',
    )
    user_name = fields.Char(
        string='User Name',
    )

    password = fields.Char(
        string='Password',
    )

from odoo import api, fields, models

class ResCompanyInheritance(models.Model):
    _inherit = 'res.company'

    is_api_allowed = fields.Boolean(
        string='Is API Allowed'
    )
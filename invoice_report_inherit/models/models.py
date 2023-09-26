from odoo import api, fields, models


class CompanyInherit(models.Model):
    _inherit = 'res.company'

    fax = fields.Char(string='Fax')
    company_gct = fields.Char(string='GCT')

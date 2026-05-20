from odoo import api, fields, models
import json
import requests

from odoo.exceptions import ValidationError

# DB = 'shakilkhan8-aladin-beauty-uat-30856289'
# UserName = 'api'
# Password = 'admin'
#
# BASE_URL = 'https://shakilkhan8-aladin-beauty-uat-30856289.dev.odoo.com'
AUTH_URL = '/web/session/authenticate'
PRODUCT_URL = '/api/create_product'

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        res = super().button_validate()
        for rec in self.move_ids_without_package:
            if rec.product_tmpl_id and rec.quantity_done:
                rec.product_tmpl_id.send_product_data()
        return res

class ProductProductInherit(models.Model):
    _inherit = "product.template"

    # def _compute_quantities(self):
    #     res = super()._compute_quantities()
    #     self.send_product_data()
    #     return res



    def send_product_data(self):
        for rec in self:
            api_config = self.env['api.configuration'].sudo().search([], limit=1)
            if not api_config:
                raise ValidationError('Please create API configuration and add all API required parameters !')

            if not (api_config.url and api_config.db_name and api_config.user_name and api_config.password):
                raise ValidationError('Please add all API required parameters !')

            url = api_config.url + AUTH_URL
            payload = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "db": api_config.db_name,
                    "login": api_config.user_name,
                    "password": api_config.password,
                }
            }
            headers = {
                'Content-Type': 'application/json',
            }
            response = requests.request(method='GET', url=url, headers=headers, json=payload)
            if response.status_code == 200 and response.cookies.values():
                session_id = response.cookies.values()[0]

                headers['Token_id'] = session_id
                url = api_config.url + PRODUCT_URL
                variant = self.env['product.product'].search([
                    ('product_tmpl_id', '=', rec.id),
                ])
                if variant:
                    payload = {
                        "data": {
                            "id": variant.id,
                            "name": rec.name,
                            "default_code": rec.default_code,
                            "list_price": rec.list_price,
                            "detailed_type": "product",
                            "qty": rec.qty_available,
                        }
                    }

                    response = requests.post(
                        url=url,
                        json=payload,
                        headers={
                            "Content-Type": "application/json",
                            "Token_id": session_id
                        },
                        timeout=30
                    )
            else:
                raise ValidationError('Un-Autherized request !')


class ResPartnerInherit(models.Model):
    _inherit = "res.partner"

    is_biller_partner = fields.Boolean(string="Is Biller Partner")

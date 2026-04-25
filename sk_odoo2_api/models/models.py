from odoo import api, fields, models
import json
import requests

DB = 'shakilkhan8-aladin-beauty-uat-30856289'
UserName = 'api'
Password = 'admin'

BASE_URL = 'https://shakilkhan8-aladin-beauty-uat-30856289.dev.odoo.com'
AUTH_URL = '/web/session/authenticate'
PRODUCT_URL = '/api/create_product'

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        res = super().button_validate()
        for rec in self.move_ids_without_package:
            if rec.product_id and rec.quantity_done:
                rec.product_id.send_product_data()
        return res

class ProductProductInherit(models.Model):
    _inherit = "product.template"

    def _compute_quantities(self):
        res = super()._compute_quantities()
        self.send_product_data()
        return res


    def send_product_data(self):
        for rec in self:
            url = BASE_URL + AUTH_URL
            payload = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "db": DB,
                    "login": UserName,
                    "password": Password
                }
            }
            headers = {
                'Content-Type': 'application/json',
            }
            response = requests.request(method='GET', url=url, headers=headers, json=payload)

            session_id = response.cookies.get_dict()['session_id']

            headers['Token_id'] = session_id
            url = BASE_URL + PRODUCT_URL
            payload = {
                "data": {
                    "id": rec.id,
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


class ResPartnerInherit(models.Model):
    _inherit = "res.partner"

    is_biller_partner = fields.Boolean(string="Is Biller Partner")

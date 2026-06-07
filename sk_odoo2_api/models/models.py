import re

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
            if rec.product_tmpl_id.api_id:
                if rec.product_tmpl_id and rec.quantity_done:
                    rec.product_tmpl_id.send_product_data()
        return res


class ProductProductInherit(models.Model):
    _inherit = "product.template"

    api_id = fields.Integer('API ID')

    # @api.onchange('qty_available')
    # def _onchange_qty_available(self):
    #     for rec in self:
    #         rec.send_product_data()

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        res['default_code'] = self.unique_sku_number() + 1
        return res

    def unique_sku_number(self):
        self.env.cr.execute("""
            SELECT COALESCE(MAX(CAST(REGEXP_REPLACE(default_code, '\D', '', 'g') AS BIGINT)), 0)
            FROM product_product
            WHERE default_code IS NOT NULL
            AND REGEXP_REPLACE(default_code, '\D', '', 'g') <> ''
        """)

        return int(self.env.cr.fetchone()[0])

    @api.model
    def create(self, vals_list):
        res = super().create(vals_list)
        if not res.api_id:
            self.send_new_product_data(vals={
                'name': res.name,
                'template_image': res.image_1920,
                'barcode': res.barcode,
                'id': res.id,

            })
        return res


    def write(self, vals):
        res = super().write(vals)
        if not self.api_id:
            self.send_product_data()
        return res

    def send_product_data(self):
        for rec in self:
            api_config = self.env['api.configuration'].sudo().search([], limit=1)
            url = api_config.url + AUTH_URL

            session_id = self.get_session_id()

            headers = {
                'Content-Type': 'application/json',
            }
            # response = requests.request(method='GET', url=url, headers=headers, json=payload)
            # if response.status_code == 200 and response.cookies.values():
            #     session_id = response.cookies.values()[0]
            if session_id:
                headers['Token_id'] = session_id
                url = api_config.url + PRODUCT_URL
                variant = self.env['product.product'].search([
                    ('product_tmpl_id', '=', rec.id),
                ])

                variant = self.env['product.product'].search([
                    ('product_tmpl_id', '=', rec.id),
                ])

                if variant:

                    # Template attributes
                    template_attributes = []

                    for line in rec.attribute_line_ids:
                        template_attributes.append({
                            'attribute': line.attribute_id.name,
                            'values': line.value_ids.mapped('name'),
                        })

                    for var in variant:

                        variant_attributes = []

                        for ptav in var.product_template_attribute_value_ids:
                            variant_attributes.append({
                                'attribute': ptav.attribute_id.name,
                                'value': ptav.product_attribute_value_id.name,
                            })

                        payload = {
                            "data": {
                                "template_id": rec.id,
                                "template_name": rec.name,
                                "template_image": rec.image_1920.decode('utf-8') if rec.image_1920 else False,
                                "detailed_type": rec.detailed_type,

                                "image": var.image_1920.decode('utf-8') if var.image_1920 else False,

                                "variant_id": var.id,
                                "variant_name": var.name,
                                "default_code": var.default_code,
                                "barcode": var.barcode,
                                "list_price": var.list_price,
                                "qty": var.qty_available,

                                "attributes": template_attributes,
                                "variant_attributes": variant_attributes,
                            }
                        }
                    
                        response = requests.post(
                            url=url,
                            json=payload,
                            headers={
                                "Content-Type": "application/json",
                                "Authorization": f"Bearer {session_id}",
                            },
                            timeout=30
                        )

    def send_new_product_data(self, vals):
        product = self.browse(vals.get('id'))
        for rec in product:
            api_config = self.env['api.configuration'].sudo().search([], limit=1)
            url = api_config.url + AUTH_URL

            headers = {
                'Content-Type': 'application/json',
            }
            session_id = self.get_session_id()
            if session_id:

                headers['Token_id'] = session_id
                url = api_config.url + PRODUCT_URL


                variant = self.env['product.product'].search([
                    ('product_tmpl_id', '=', product.id),
                ])

                if variant:

                    # Template attributes
                    template_attributes = []

                    for line in rec.attribute_line_ids:
                        template_attributes.append({
                            'attribute': line.attribute_id.name,
                            'values': line.value_ids.mapped('name'),
                        })
                    for var in variant:
                        variant_attributes = []

                        for ptav in var.product_template_attribute_value_ids:
                            variant_attributes.append({
                                'attribute': ptav.attribute_id.name,
                                'value': ptav.product_attribute_value_id.name,
                            })

                        payload = {
                            "data": {
                                "template_id": product.id,
                                "template_name": product.name,
                                "variant_id": var.id,
                                "template_image": rec.image_1920.decode('utf-8') if rec.image_1920 else False,
                                "detailed_type": rec.detailed_type,

                                "image": var.image_1920.decode('utf-8') if var.image_1920 else False,
                                "variant_name": var.name,
                                "default_code": var.default_code,
                                "barcode": vals.get('barcode', ''),
                                "list_price": var.list_price,
                                "qty": var.qty_available,

                                "attributes": template_attributes,
                                "variant_attributes": variant_attributes,
                            }
                        }

                        response = requests.post(
                            url=url,
                            json=payload,
                            headers={
                                "Content-Type": "application/json",
                                "Authorization": f"Bearer {session_id}",
                            },
                            timeout=30
                        )
    def get_session_id(self):
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
            return session_id
        else:
            return None

class ProductVariantInherit(models.Model):
    _inherit = "product.product"

    api_id = fields.Integer('API ID')

    # @api.model
    # def create(self, vals):
    #     vals['default_code'] = self.unique_sku_number() + 1
    #     print(self.unique_sku_number())
    #     res = super().create(vals)
    #
    #     return res
    #
    #
    # def write(self, vals):
    #     res = super().write(vals)
    #     if self.product_tmpl_id:
    #         self.product_tmpl_id.send_product_data()
    #     return res

    def unique_sku_number(self):
        self.env.cr.execute("""
            SELECT COALESCE(MAX(CAST(REGEXP_REPLACE(default_code, '\D', '', 'g') AS BIGINT)), 0)
            FROM product_product
            WHERE default_code IS NOT NULL
            AND REGEXP_REPLACE(default_code, '\D', '', 'g') <> ''
        """)

        return int(self.env.cr.fetchone()[0])




class ResPartnerInherit(models.Model):
    _inherit = "res.partner"

    is_biller_partner = fields.Boolean(string="Is Biller Partner")




import re

import requests
import json

from odoo import api, fields, models
from odoo.exceptions import ValidationError

AUTH_URL = '/web/session/authenticate'
PRODUCT_URL = '/api/create_product'
PRODUCT_UPDATE_IMAGES_URL = '/api/update-product-images'
PRODUCT_TEMPLATE_UPDATE_URL = '/api/update-product-template'
UPDATE_VARIANT_URL = '/api/create-product-variant'

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        res = super().button_validate()
        for rec in self.move_ids_without_package:
            if rec.product_tmpl_id.api_id:
                if rec.product_tmpl_id and rec.quantity:
                    rec.product_tmpl_id.update_template()
        return res


class ProductProductInherit(models.Model):
    _inherit = "product.template"

    api_id = fields.Integer("API ID")
    code = fields.Char("Code")
    sync_on = fields.Boolean(
        string='Syncing On'
    )

    def update_variant_codes(self):
        for rec in self.product_variant_ids:
            rec.update_variant()

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        res['default_code'] = str(self.unique_sku_number() + 1)

        return res

    def unique_sku_number(self):

        products = self.env['product.product'].search([
            ('active', '=', True),
            ('default_code', '!=', False)
        ])

        numbers = []

        for product in products:
            sku = product.default_code
            numeric_part = ''.join(char for char in sku if sku.isdigit())
            if numeric_part:
                numbers.append(int(numeric_part))

        return max(numbers, default=0)

    @api.model
    def create(self, vals_list):
        res = super().create(vals_list)

        if not res.api_id:
            result = self.send_new_product_data(vals={
                'name': res.name,
                'template_image': res.image_1920,
                'barcode': res.barcode,
                'id': res.id,
                'lst_price': res.list_price,
                'detailed_type': res.detailed_type,
                'standard_price': res.standard_price,
                'sync_on': res.sync_on,  # ✅ typo fix
                'weight': res.weight,
            })
            if result:
                if result.status_code == 200:
                    result1 = res.create_variants()

        return res

    # def write(self, vals):
    #     if 'attribute_line_ids' in vals:
    #         for rec in self.product_variant_ids:
    #             self.env['store.deleted.sequence'].create({
    #                 'name': rec.default_code
    #             })
    #     res = super().write(vals)
    #
    #     for rec in self:
    #         if not rec.api_id:
    #             rec.update_template()
    #             rec.update_variants()
    #     return res

    def write(self, vals):
        if 'attribute_line_ids' in vals:
            for rec in self.product_variant_ids:
                self.env['store.deleted.sequence'].create({
                    'name': rec.default_code
                })
        res = super().write(vals)

        if self.env.context.get('skip_api_sync'):
            return res

        for rec in self:
            if not rec.api_id:
                rec.update_template()
                rec.update_variants()
        return res

    #This function used to create variants during creation of templates
    def create_variants(self):
        att_vals = []
        for rec in self:
            for line in self.attribute_line_ids:
                for attr in line.value_ids:
                    att_vals.append({
                        'attribute': attr.attribute_id.name,
                        'value': attr.name
                    })

            api_config = self.env['api.configuration'].sudo().search([], limit=1)
            url = f"{api_config.url}{AUTH_URL}"
            if not api_config:
                continue

            session_id = self.get_session_id()

            headers = {
                'Content-Type': 'application/json',
            }

            payload = {
                'data': {
                    'api_id': rec.id,
                    'attribute_values': att_vals,
                    'variant_ids': rec.product_variant_ids.ids
                }
            }

            if session_id:
                headers['Token_id'] = session_id
                url = f"{api_config.url}{UPDATE_VARIANT_URL}"
                response = requests.post(
                    url=url,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {session_id}",
                    },
                    timeout=30
                )

                return response

    #this function used to update or create new variants against template
    def update_variants(self, data=None):
            att_vals = []
            if data:

                api_config = self.env['api.configuration'].sudo().search([], limit=1)
                url = f"{api_config.url}{AUTH_URL}"
                if not api_config:
                    return True

                session_id = self.get_session_id()

                headers = {
                    'Content-Type': 'application/json',
                }

                payload = data

                if session_id:
                    headers['Token_id'] = session_id
                    url = f"{api_config.url}{UPDATE_VARIANT_URL}"
                    response = requests.post(
                        url=url,
                        json=payload,
                        headers={
                            "Content-Type": "application/json",
                            "Authorization": f"Bearer {session_id}",
                        },
                        timeout=30
                    )

                    return response

    def update_template(self):
        for rec in self:
            api_config = self.env['api.configuration'].sudo().search([], limit=1)
            url = f"{api_config.url}{AUTH_URL}"
            if not api_config:
                continue
            session_id = self.get_session_id()

            headers = {
                'Content-Type': 'application/json',
            }

            if session_id:
                headers['Token_id'] = session_id
                url = f"{api_config.url}{PRODUCT_TEMPLATE_UPDATE_URL}"
                variant = self.env['product.product'].search([
                    ('product_tmpl_id', '=', rec.id),
                ])

                payload = {
                            "data": {
                            "product_id": self.id,
                            'name': self.name,
                            'image_1920': self.image_1920,
                            'barcode': self.barcode,
                            'lst_price': self.list_price,
                            'detailed_type': self.detailed_type,
                            'standard_price': self.standard_price,
                            'sync_on': self.sync_on,
                            'weight': self.weight,
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
            if not api_config or not api_config.url:
                continue
            url = f"{api_config.url}{AUTH_URL}"

            headers = {
                'Content-Type': 'application/json',
            }

            session_id = self.get_session_id()
            if session_id:

                headers['Token_id'] = session_id
                url = f"{api_config.url}{PRODUCT_URL}"


                payload = {
                            "data": {
                            "name": vals.get('name'),
                            "api_id": vals.get('id'),
                            "template_image": vals.get('template_image'),
                            "id": vals.get('id'),
                            "barcode": vals.get('barcode'),
                            "lst_price": vals.get('lst_price'),
                            "detailed_type": vals.get('detailed_type'),
                            'standard_price': vals.get('standard_price', 0),
                            'sync_on': vals.get('sync_on', False),
                            'weight': vals.get('weight', 0),
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
                return response

    def get_session_id(self):
        api_config = self.env['api.configuration'].sudo().search([], limit=1)
        if not api_config:
            raise ValidationError('Please create API configuration and add all API required parameters !')

        url = f"{api_config.url}{AUTH_URL}"
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

    api_id = fields.Integer("API ID")

    sync_on = fields.Boolean(
        string='Syncing On'
    )


    standard_price = fields.Float(
        'Cost', company_dependent=False,
        digits='Product Price',
        groups="base.group_user",
        help="""Value of the product (automatically computed in AVCO).
                Used to value the product when the purchase cost is not known (e.g. inventory adjustment).
                Used to compute margins on sale orders.""")


    def action_update_odoo2_bulk(self):
        api_config = self.env['api.configuration'].sudo().search([], limit=1)
        if not api_config:
            raise ValidationError('Please create API configuration and add all API required parameters !')

        session_id = self.get_session_id()
        if not session_id:
            raise ValidationError('Odoo2 se authenticate nahi ho saka. URL/DB/Username/Password check karein.')

        url = api_config.url + '/api/update_product_in_bulk'
        headers = {
            'Content-Type': 'application/json',
            'Token_id': session_id,
        }

        for variant in self:
            if not variant.default_code:
                continue

            payload = {
                'data': {
                    'internal_reference': variant.default_code,
                    'weight': variant.weight,
                    'standard_price': variant.standard_price,
                    'image': variant.image_1920.decode('utf-8') if variant.image_1920 else False,
                }
            }

            response = requests.post(url, headers=headers, json=payload, timeout=30)
            result = response.json()

            if result.get('status') != 'success':
                # log kar do, taake pata chale kaun sa variant fail hua
                import logging
                logging.getLogger(__name__).warning(
                    "Variant %s (default_code=%s) Odoo2 par update nahi ho saka: %s",
                    variant.id, variant.default_code, result.get('message')
                )

    # sync product using default code
    def action_sync_products(self):
        api_config = self.env['api.configuration'].sudo().search([], limit=1)
        if not api_config:
            raise ValidationError('Please create API configuration and add all API required parameters!')

        session_id = self.get_session_id()
        if not session_id:
            raise ValidationError('Unable to authenticate with API.')

        products_with_code = self.filtered(lambda p: p.default_code)

        if not products_with_code:
            raise ValidationError('Selected products do not have a Default Code (SKU) set.')

        default_codes = products_with_code.mapped('default_code')

        payload = {
            'data': {
                'default_codes': default_codes
            }
        }

        url = f"{api_config.url}/api/sync-product-by-code"

        response = requests.post(
            url=url,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {session_id}",
            },
            timeout=90
        )

        if response.status_code != 200:
            raise ValidationError(f"API request failed with status {response.status_code}")

        response_data = response.json()
        # type='json' route ka response 'result' key ke andar wrap hota hai
        result = response_data.get('result', response_data)

        if result.get('status') != 'success':
            raise ValidationError(result.get('message', 'Sync failed.'))

        matched_data = result.get('data', [])

        for item in matched_data:
            if not item.get('found'):
                continue

            default_code = item.get('default_code')
            product_id = item.get('product_id')
            template_id = item.get('template_id')

            product = products_with_code.filtered(lambda p: p.default_code == default_code)

            if product:
                product.write({
                    'api_id': product_id,
                    'sync_on': True,
                })
                if template_id:
                    product.product_tmpl_id.write({
                        'api_id': template_id,
                        'sync_on': True,
                    })

        return True



    def write(self, vals):
        res = super().write(vals)
        self.update_variant()
        return res


    @api.model_create_multi
    def create(self, vals_list):
        products = super().create(vals_list)
        next_no = self.unique_sku_number()
        i = 1

        is_api = []
        for index, product in enumerate(products):
            vals = vals_list[index] if index < len(vals_list) else {}

            if not product.default_code:
                product.default_code = next_no + i
                i += 1

            # Odoo ka automatic variant-generation flow 'sync_on' kabhi
            # vals mein nahi bhejta (ye related/computed nahi hai template se),
            # isliye jab explicitly na diya ho, template ki value le lo.
            if 'sync_on' not in vals:
                product.sync_on = product.product_tmpl_id.sync_on

            if not product.api_id:
                is_api.append(True)

            att_vals = []
            for line in product.attribute_line_ids:
                for attr in line.value_ids:
                    att_vals.append({
                        'attribute': attr.attribute_id.name,
                        'value': attr.name
                    })

        payload = {
            'data': {
                'api_id': product.product_tmpl_id.id,
                'attribute_values': att_vals,
                'variant_ids': sorted(products.ids),
                'ids_and_values': [{
                    'id': rec.id,
                    'default_code': rec.default_code,
                    'sync_on': rec.sync_on,
                    'weight': rec.weight,
                } for rec in sorted(products)],
            }
        }
        if is_api and not self.env.context.get('skip_api_sync'):
            self.product_tmpl_id.update_variants(data=payload)

        return products

    def unique_sku_number(self):

        products = self.env['product.product'].search([
            ('active', '=', True),
            ('default_code', '!=', False)
        ])
        numbers = []

        for product in products:
            sku = product.default_code
            numeric_part = ''.join(char for char in sku if sku.isdigit())
            if numeric_part:
                numbers.append(int(numeric_part))

        return max(numbers, default=0)


    def update_odoo2_product_images(self):
        session_id = self.get_session_id()

        for rec in self:

            payload = {
                'data': {
                    'product_id': rec.id,
                    'image_1920': rec.image_1920.decode('utf-8') if rec.image_1920 else False,
                    'default_code': rec.default_code
                }
            }

            api_config = self.env['api.configuration'].sudo().search([], limit=1)

            url = api_config.url + PRODUCT_UPDATE_IMAGES_URL

            response = requests.post(
                url=url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {session_id}",
                },
                timeout=30
            )


    def update_variant(self):

        session_id = self.get_session_id()
        for rec in self:
            if not rec.api_id:
                product_id = rec.id if isinstance(rec.id, int) else rec._origin.id
                payload = {
                    'data': {
                        'product_id': product_id,
                        'name': rec.name,
                        'list_price': rec.list_price,
                        'image_1920': rec.image_1920.decode('utf-8') if rec.image_1920 else False,
                        'barcode': rec.barcode,
                        'standard_price': rec.standard_price,
                        'detailed_type': rec.detailed_type,
                        'default_code': rec.default_code,
                        'qty': rec.qty_available,
                        'sync_on': rec.sync_on,
                        'weight': rec.weight,
                    }
                }

                api_config = self.env['api.configuration'].sudo().search([], limit=1)
                url = api_config.url + '/api/update-product-variant'

                response = requests.post(
                    url=url,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                    },
                    cookies={
                        "session_id": session_id,
                    },
                    timeout=30
                )

                response = response


    def get_session_id(self):
        api_config = self.env['api.configuration'].sudo().search([], limit=1)
        if not api_config:
            raise ValidationError('Please create API configuration and add all API required parameters !')


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




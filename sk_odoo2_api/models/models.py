import re
from collections import defaultdict
from zope.interface.common import sequence

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
UPDATE_VARIANT_URL = '/api/create-product-variant'
PRODUCT_TEMPLATE_UPDATE_URL = '/api/update-product-template'

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        res = super().button_validate()
        for rec in self.move_ids_without_package:
            if not rec.product_id.api_id:
                if rec.product_id and (rec.quantity_done or rec.product_uom_qty):
                    rec.product_id.update_variant()
        return res


class ProductProductInherit(models.Model):
    _inherit = "product.template"

    api_id = fields.Integer('API ID')

    code = fields.Char(
        string='Code',
        store=True,
    )

    def unlink(self):
        old_seq = [{
            'name': rec.default_code,
            'is_active': True
        } for rec in self.product_variant_ids]
        self.env['store.deleted.sequence'].create(old_seq)
        # self.env['store.deleted.sequence'].search([]).unlink()
        res = super().unlink()
        return res


    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        exist = self.is_code_exist(code=self.unique_sku_number() + 1)

        res['default_code'] = exist
        return res

    def is_code_exist(self, code):
        company_id = self.env['res.company'].search([
            ('is_api_allowed', '=', True)
        ], limit=1)

        products = self.env['product.product'].search([
            ('default_code', '=', code),
            ('active', '=', True),
            ('company_id', '=', company_id.id),
        ])
        if products:
            return code + 1
        else:
            return code

    def unique_sku_number(self):
        company = self.env['res.company'].search([
            ('is_api_allowed', '=', True)
        ], limit=1)
    
        if not company:
            return 0
    
        products = self.env['product.product'].search([
            ('default_code', '!=', False),
            ('active', '=', True),
            ('company_id', '=', company.id),
        ])
    
       
    
        numeric_products = []
    
        for product in products:
            code = (product.default_code or '').strip()
    
            if code.isdigit():
                numeric_products.append(
                    (int(code), code, product.id)
                )
    
        numeric_products.sort(
            key=lambda x: x[0],
            reverse=True
        )
    
        return numeric_products[0][0] if numeric_products else 0
    
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
                'default_code': res.default_code

            })
            if result.status_code == 200:
                result1 = res.create_variants()

        return res

    def write(self, vals):

        if 'attribute_line_ids' in vals:
            preserve_sequence = self.env['store.deleted.sequence'].search([]).unlink()
            old_seq = [{
                'name': rec.default_code,
                'is_active': True
            } for rec in self.product_variant_ids]
            self.env['store.deleted.sequence'].create(old_seq)
            # self.env['store.deleted.sequence'].search([]).unlink()

        res = super().write(vals)

        for rec in self:
            if not rec.api_id:
                rec.update_template()
                rec.update_variants()
        return res

     # This function used to create variants during creation of templates
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
                if not api_config:
                    continue

                session_id = self.get_session_id()

                headers = {
                    'Content-Type': 'application/json',
                }
                product_id = rec.id if isinstance(rec.id, int) else rec._origin.id
                payload = {
                    'data': {
                        'api_id': product_id,
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
            # this function used to update or create new variants against template

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
                        'image_1920': self.image_1920.decode('utf-8') if self.image_1920 else False,
                        'barcode': self.barcode,
                        'lst_price': self.list_price,
                        'detailed_type': self.detailed_type,
                        'standard_price': self.standard_price or 0.0,
                        'qty': self.qty_available or 0.0,
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
                            "default_code": vals.get('default_code'),
                            'standard_price': vals.get('standard_price'),
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

    api_id = fields.Integer("API ID")

    standard_price = fields.Float(
        'Cost', company_dependent=False,
        digits='Product Price',
        groups="base.group_user",
        help="""Value of the product (automatically computed in AVCO).
                Used to value the product when the purchase cost is not known (e.g. inventory adjustment).
                Used to compute margins on sale orders.""")

    def write(self, vals):
        res = super().write(vals)
        self.update_variant()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        products = super().create(vals_list)

        reserved = self.env['store.deleted.sequence'].search([]).mapped('name')
        seq_list = sorted(list(set(reserved)))
        next_no = self.unique_sku_number()
        sequence_to_delete = []

        is_api = []

        #this code is used to create a consecutive sequence with increment of 1
        for product in products:
            if not product.api_id:
                is_api.append(True)
            if not product.default_code:
                if seq_list:
                    if next_no in sequence_to_delete and str(next_no) in seq_list:
                        seq_list.remove(str(next_no))
                        # continue

                    if int(next_no) > (int(seq_list[0]) if seq_list else 0):
                        product.default_code = seq_list[0]
                        sequence_to_delete.append(seq_list[0])
                        seq_list.pop(0)

                    elif int(next_no) == (int(seq_list[0]) if seq_list else 0):
                        product.default_code = seq_list[0]
                        sequence_to_delete.append(seq_list[0])
                        seq_list.pop(0)

                    else:
                        next_no += 1
                        product.default_code = next_no
                        sequence_to_delete.append(next_no)
                else:
                    next_no += 1
                    product.default_code = next_no
                    sequence_to_delete.append(next_no)

        self.env['store.deleted.sequence'].search([('name', 'in', sequence_to_delete)]).unlink()

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
                    'variant_ids': products.ids,
                }
            }
        if is_api:
            self.product_tmpl_id.update_variants(data=payload)

        return products

    def unique_sku_number(self):
        company = self.env['res.company'].search([
            ('is_api_allowed', '=', True)
        ], limit=1)
    
        if not company:
            return 0
    
        products = self.env['product.product'].search([
            ('default_code', '!=', False),
            ('active', '=', True),
            ('product_tmpl_id.active', '=', True),
            ('product_tmpl_id.company_id', '=', company.id),
        ])
    
        max_code = 0
    
        for product in products:
            default_code = (product.default_code or '').strip()
    
            # Only pure integer default_code
            if default_code.isdigit():
    
                number = int(default_code)
    
                if number > max_code:
                    max_code = number
    
        return max_code

    def update_variant(self):

        session_id = self.get_session_id()
        for rec in self:
            if not rec.api_id:
                product_id = rec.id if isinstance(rec.id, int) else rec._origin.id
                payload = {
                    'data': {
                        'product_id': product_id,
                        'name': rec.name,
                        'lst_price': rec.list_price,
                        'image_1920': rec.image_1920.decode('utf-8') if rec.image_1920 else False,
                        'barcode': rec.barcode,
                        'detailed_type': rec.detailed_type,
                        'standard_price': rec.standard_price,
                        'qty': rec.qty_available,
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




class ResPartnerInherit(models.Model):
    _inherit = "res.partner"

    is_biller_partner = fields.Boolean(string="Is Biller Partner")




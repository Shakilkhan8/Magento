from odoo import http
from odoo.http import request

from collections import defaultdict

class ProductAPI(http.Controller):

    @http.route('/api/create_product', type='json', auth='public', methods=['POST'], csrf=False)
    def create_product(self, **kwargs):
        try:
            vals = request.httprequest.json.get('data', {})

            ProductTemplate = request.env['product.template'].sudo()
            ProductAttribute = request.env['product.attribute'].sudo()
            ProductAttributeValue = request.env['product.attribute.value'].sudo()

            # --------------------------------------------------
            # Template Search
            # --------------------------------------------------

            template = ProductTemplate.search([
                ('api_id', '=', vals.get('api_id'))
            ], limit=1)

            # --------------------------------------------------
            # Create Attributes / Values
            # --------------------------------------------------
            company_id = request.env['res.company'].sudo().search([
                ('is_api_allowed', '=', True)
            ], limit=1)

            template_vals = {
                'name': vals.get('name'),
                'list_price': vals.get('lst_price', 0),
                'image_1920': vals.get('template_image', False),
                'detailed_type': vals.get('detailed_type'),
                'company_id': company_id.id,
                'default_code': vals.get('default_code'),
                'barcode': vals.get('default_code', False),
                'api_id': vals.get('api_id'),
            }

            template = ProductTemplate.sudo().create(template_vals)

            return {
                'status': 'success',
                'product_id': template.id,
            }

        except Exception as e:
            return {'status': 'error', 'message': str(e)}



    @http.route('/api/create-product-variant', type='json', auth='public', methods=['POST'], csrf=False)
    def create_product_variant(self, **kwargs):

        data = request.httprequest.json.get('data', {})

        template = request.env["product.template"].sudo().search(
            [("api_id", "=", data.get("api_id"))],
            limit=1
        )

        if not template:
            return {
                "success": False,
                "message": "Product template not found."
            }

        grouped_attributes = defaultdict(list)

        for line in data.get("attribute_values", []):

            attribute = request.env["product.attribute"].sudo().search(
                [("name", "=", line["attribute"])],
                limit=1
            )

            if not attribute:
                attribute = request.env["product.attribute"].sudo().create({
                    "name": line["attribute"],
                    "create_variant": "always",
                })

            value = request.env["product.attribute.value"].sudo().search(
                [
                    ("attribute_id", "=", attribute.id),
                    ("name", "=", line["value"])
                ],
                limit=1
            )

            if not value:
                value = request.env["product.attribute.value"].sudo().create({
                    "attribute_id": attribute.id,
                    "name": line["value"],
                })
            grouped_attributes[attribute.id].append(value.id)

        vals = {
            "attribute_line_ids": []
        }

        for attribute_id, value_ids in grouped_attributes.items():
            existing_line = template.attribute_line_ids.filtered(
                lambda l: l.attribute_id.id == attribute_id
            )

            if existing_line:
                # Existing values
                old_values = existing_line.value_ids.ids

                # Merge new values
                new_values = list(set(old_values + value_ids))

                existing_line.write({
                    "value_ids": [(6, 0, new_values)]
                })

            else:
                vals["attribute_line_ids"].append(
                    (
                        0,
                        0,
                        {
                            "attribute_id": attribute_id,
                            "value_ids": [(6, 0, value_ids)]
                        }
                    )
                )

        if vals["attribute_line_ids"]:
            variant_ids = data.get('variant_ids')
            template.write(vals)
            i = 0
            if len(variant_ids) == len(template.product_variant_ids):
                for rec in template.product_variant_ids:
                    rec.api_id = variant_ids[i]
                    i +=1

        return {
            'message': template.product_variant_ids.ids
        }

    @http.route('/api/update-product-images', type='json', auth='public', methods=['POST'], csrf=False)
    def update_product_images(self, **kwargs):
        company_id = request.env['res.company'].sudo().search([
            ('is_api_allowed', '=', True)
        ], limit=1)

        try:
            vals = request.httprequest.json.get('data', {})

            if 'product_id' in vals and 'default_code' in vals:
                default_code = vals.get('default_code')
                product = request.env['product.product'].sudo().search([
                    ('default_code', '=', default_code)
                ], limit=1)

                if not product:
                    return {'status': 'error', 'message': 'Product not found'}
                else:
                    product.sudo().write({
                        'image_1920': vals.get('image_1920') if vals.get('image_1920') else product.image_1920,
                        'api_id': vals.get('product_id')
                    })

                    return {
                        'status': 'success',
                        'message': {
                            'barcode': product.barcode,
                            'list_price': product.list_price,
                        }
                    }

        except Exception as e:

            return {'status': 'error', 'message': str(e)}

    @http.route('/api/update-product-template', type='json', auth='public', methods=['POST'], csrf=False)
    def update_product_template(self, **kwargs):
        company_id = request.env['res.company'].sudo().search([
            ('is_api_allowed', '=', True)
        ], limit=1)

        try:
            vals = request.httprequest.json.get('data', {})

            if 'product_id' in vals:
                product_id = vals.get('product_id')
                product = request.env['product.template'].sudo().search([
                    ('api_id', '=', product_id)
                ], limit=1)

                if not product:
                    return {'status': 'error', 'message': 'Product not found'}
                else:
                    product.sudo().write({
                        'image_1920': vals.get('image_1920') if vals.get('image_1920') else product.image_1920,
                        'barcode': vals.get('barcode', False),
                        'list_price': vals.get('lst_price', 0),
                        'detailed_type': vals.get('detailed_type', False),
                        'name': vals.get('name', False),

                    })

                    return {
                        'status': 'success',
                        'message': {
                            'barcode': product.barcode,
                            'list_price': product.list_price,
                            'name': product.name,
                        }
                    }

        except Exception as e:

            return {'status': 'error', 'message': str(e)}


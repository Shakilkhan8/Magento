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

            # attribute_line_ids = []
            #
            # for attr_data in vals.get('attribute_values', []):
            #
            #     attribute = ProductAttribute.search([
            #         ('name', '=', attr_data.get('attribute'))
            #     ], limit=1)
            #
            #     if not attribute:
            #         attribute = ProductAttribute.create({
            #             'name': attr_data.get('attribute'),
            #             # 'company_id': company_id.id
            #         })
            #
            #     value_ids = []
            #
            #     for value_name in attr_data.get('values', []):
            #
            #         value = ProductAttributeValue.search([
            #             ('name', '=', value_name),
            #             ('attribute_id', '=', attribute.id),
            #         ], limit=1)
            #
            #         if not value:
            #             value = ProductAttributeValue.create({
            #                 'name': value_name,
            #                 'attribute_id': attribute.id,
            #                 # 'company_id': company_id.id
            #             })
            #
            #         value_ids.append(value.id)
            #
            #     attribute_line_ids.append((0, 0, {
            #         'attribute_id': attribute.id,
            #         'value_ids': [(6, 0, value_ids)]
            #     }))

            # --------------------------------------------------
            # Create Template
            # --------------------------------------------------

            template_vals = {
                'name': vals.get('name'),
                'list_price': vals.get('lst_price', 0),
                'image_1920': vals.get('template_image', False),
                'detailed_type': vals.get('detailed_type'),
                'company_id': company_id.id,
                'default_code': vals.get('default_code'),
                'barcode': vals.get('default_code', False),
            }

            if not template:

                template_vals['api_id'] = vals.get('api_id')
                # template_vals['attribute_line_ids'] = attribute_line_ids

                template = ProductTemplate.sudo().create(template_vals)
                variants = request.env['product.product'].search([
                    ('product_tmpl_id', '=', template.id)
                ])


                if variants:
                    for var in variants:
                        var.sudo().image_1920 = vals.get('template_image', False)
            else:

                template.write(template_vals)
                variants = request.env['product.product'].sudo().search([
                    ('product_tmpl_id', '=', template.id)
                ])

                if variants:
                    for var in variants:
                        var.image_1920 = vals.get('template_image')

                # Rebuild attributes only if payload contains them
                # if attribute_line_ids:
                #     template.attribute_line_ids.unlink()
                #
                #     template.write({
                #         'attribute_line_ids': attribute_line_ids
                #     })

            # --------------------------------------------------
            # Find Exact Variant
            # --------------------------------------------------

            variant = template.sudo().product_variant_ids

            for attr in vals.get('variant_attributes', []):
                variant = variant.filtered(
                    lambda v: any(
                        ptav.attribute_id.name == attr.get('attribute')
                        and ptav.product_attribute_value_id.name == attr.get('value')
                        for ptav in v.product_template_attribute_value_ids
                    )
                )

            variant = variant[:1]

            # --------------------------------------------------
            # Fallback Variant
            # --------------------------------------------------

            if not variant and template.product_variant_ids:
                variant = template.product_variant_ids[0]

            # --------------------------------------------------
            # Update Variant
            # --------------------------------------------------

            if variant:

                barcode = vals.get('barcode')
                if barcode:
                    barcode = str(barcode)

                image = vals.get('image')

                variant.sudo().write({
                    'api_id': vals.get('variant_id'),
                    'barcode': barcode,
                    'image_1920': image,
                })

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
            template.write(vals)

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

    @http.route('/api/update-product-template-images', type='json', auth='public', methods=['POST'], csrf=False)
    def update_product_template_images(self, **kwargs):
        company_id = request.env['res.company'].sudo().search([
            ('is_api_allowed', '=', True)
        ], limit=1)
        try:
            vals = request.httprequest.json.get('data', {})

            if 'product_id' in vals and 'default_code' in vals:
                product_id = vals.get('product_id')
                product = request.env['product.template'].sudo().search([
                    ('api_id', '=', product_id)
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


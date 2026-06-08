from odoo import http
from odoo.http import request


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
                ('api_id', '=', vals.get('template_id'))
            ], limit=1)

            # --------------------------------------------------
            # Create Attributes / Values
            # --------------------------------------------------

            attribute_line_ids = []

            for attr_data in vals.get('attributes', []):

                attribute = ProductAttribute.search([
                    ('name', '=', attr_data.get('attribute'))
                ], limit=1)

                if not attribute:
                    attribute = ProductAttribute.create({
                        'name': attr_data.get('attribute')
                    })

                value_ids = []

                for value_name in attr_data.get('values', []):

                    value = ProductAttributeValue.search([
                        ('name', '=', value_name),
                        ('attribute_id', '=', attribute.id)
                    ], limit=1)

                    if not value:
                        value = ProductAttributeValue.create({
                            'name': value_name,
                            'attribute_id': attribute.id,
                        })

                    value_ids.append(value.id)

                attribute_line_ids.append((0, 0, {
                    'attribute_id': attribute.id,
                    'value_ids': [(6, 0, value_ids)]
                }))

            # --------------------------------------------------
            # Create Template
            # --------------------------------------------------

            template_vals = {
                'name': vals.get('template_name'),
                'list_price': vals.get('list_price', 0),
                'image_1920': vals.get('template_image'),
                'detailed_type': vals.get('detailed_type')
            }

            if not template:

                template_vals['api_id'] = vals.get('template_id')
                template_vals['attribute_line_ids'] = attribute_line_ids

                template = ProductTemplate.sudo().create(template_vals)
                variants = request.env['product.product'].search([
                    ('product_tmpl_id', '=', template.id)
                ])
                if variants:
                    for var in variants:
                        var.sudo().image_1920 = vals.get('template_image')

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
                    'default_code': vals.get('default_code'),
                    'barcode': barcode,
                    'image_1920': image,
                })


            # Warehouse
            warehouse = request.env['stock.warehouse'].sudo().search([
                ('code', '=', 'IMR')
            ], limit=1)

            if not warehouse:
                return {'status': 'error', 'message': 'Warehouse not found'}

            location = warehouse.lot_stock_id

            # Inventory adjustments only apply when inventory_mode=True (stock.quant inverse).
            inv_ctx = dict(request.env.context or {}, inventory_mode=True)
            Quant = request.env['stock.quant'].sudo().with_context(inv_ctx)

            quant = Quant.search([
                ('product_id', '=', variant.id),
                ('location_id', '=', location.id),
            ], limit=1)

            qty = vals.get('qty')
            if not quant:
                quant = Quant.create({
                    'product_id': variant.id,
                    'location_id': location.id,
                })

            # Check for tracking
            if variant.tracking != 'none':
                return {'status': 'error', 'message': f'Product  is tracked by {variant.tracking}. Lot/Serial required.'}

            # Sets counted qty and creates stock moves (Directly apply as SUPERUSER to bypass permission/UI checks).
            from odoo import SUPERUSER_ID
            quant.with_user(SUPERUSER_ID).write({'inventory_quantity': qty})
            quant.with_user(SUPERUSER_ID)._apply_inventory()

            return {
                'status': 'success',
                'product_id': variant.id,
                'quant': quant.id,
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    @http.route('/api/update-product-variant', type='json', auth='public', methods=['POST'], csrf=False)
    def update_product_variant(self, **kwargs):
        try:
            vals = request.httprequest.json.get('data', {})

            if 'product_id' in vals:
                product_id = vals.get('product_id')
                product = request.env['product.product'].sudo().search([
                    ('api_id', '=', product_id)
                ], limit=1)

                if not product:
                    return {'status': 'error', 'message': 'Product not found'}
                else:
                    product.sudo().write({
                        'name': vals.get('name'),
                        'image_1920': vals.get('image_1920') if vals.get('image_1920') else product_id.image_1920,
                        'list_price': vals.get('list_price'),
                        'barcode': vals.get('barcode'),
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
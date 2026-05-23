# -*- coding: utf-8 -*-
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class OdooSyncController(http.Controller):

    @http.route('/web/session/authenticate', type='json', auth="none")
    def authenticate(self, db, login, password, base_location=None):
        try:
            request.session.authenticate(db, login, password)
            return {
                'status': 200,
                'message': 'Authentication successful',
                'Token_id': request.session.sid,
            }
        except Exception as e:
            return {
                'status': 500,
                'error': str(e),
            }

    @http.route('/api/create-sale-order', type='json', auth='user', csrf=False, methods=['POST'])
    def create_sale_order_data(self, **kwargs):
        try:
            data = request.httprequest.json['params']['data']
            lines = data.get('lines', [])

            partner = request.env['res.partner'].sudo().search([
                ('is_biller_partner', '=', True),
            ], limit=1)
            if not partner:
                return {'status': 'error', 'message': 'No partner found with is_biller_partner=True'}

            if not lines:
                return {'status': 'error', 'message': 'No order lines provided'}

            order_lines = []
            for line in lines:
                product = request.env['product.product'].sudo().search(
                    [('id', '=', line.get('product_id'))], limit=1
                )
                if not product:
                    return {
                        'status': 'error',
                        'message': f'Product not found for {lines}',
                    }
                order_lines.append((0, 0, {
                    'product_id': product.id,
                    'name': line.get('name', product.name),
                    'price_unit': line.get('price_unit', 0),
                    'product_uom_qty': line.get('product_uom_qty', 1),
                }))

            sale_order = request.env['sale.order'].sudo().create({
                'partner_id': partner.id,
                'api_order_id': data.get('order_Id'),
                'order_line': order_lines,
            })

            _logger.info("Sale order %s created via API", sale_order.name)
            return {
                'status': 200,
                'message': 'Sale order %s created' % sale_order.name,
                'sale_order_id': sale_order.id,
                'sale_order_name': sale_order.name,
            }

        except Exception as e:
            _logger.error("Error creating sale order via API: %s", e)
            return {
                'status': 'error',
                'message': 'Error creating sale order: %s' % str(e),
            }

    @http.route('/api/update-sale-order', type='json', auth='user', csrf=False, methods=['POST'])
    def update_sale_order_data(self, **kwargs):
        try:
            data = request.httprequest.json['data']
            order_id = data.get('order_id', [])
            state = data.get('state', [])

            order = request.env['sale.order'].sudo().search([
                ('id', '=', order_id),
            ], limit=1)
            if not order:
                return {'status': 'error', 'message': 'No order found with this ID'}

            _logger.info(f'Sale Order Object {order.id} -> {state}')
            if order and state:
                if state == 'cancel':
                    order.action_cancel()
                    order.state = 'cancel'
                if state == 'draft':
                    order.action_draft()
                    order.state = 'draft'


            _logger.info("Sale order %s update via API", order.name)
            return {
                'status': 200,
                'message': 'Sale order %s created' % order.name,
                'sale_order_id': order.id,
                'sale_order_state': order.state,
            }

        except Exception as e:
            _logger.error("Error updating sale order via API: %s", e)
            return {
                'status': 'error',
                'message': 'Error updating sale order: %s' % str(e),
            }

class ProductAPI(http.Controller):

    @http.route('/api/create_product', type='json', auth='public', methods=['POST'], csrf=False)
    def create_product(self, **kwargs):
        try:
            vals = request.httprequest.json['data']

            sku = vals.get('default_code')
            qty = float(vals.get('qty', 0))

            # Product Search
            product = request.env['product.template'].sudo().search([
                ('default_code', '=', sku)
            ], limit=1)

            if not product:
                product = request.env['product.template'].sudo().create({
                    'api_id': vals.get('id'),
                    'name': vals.get('name') or sku,
                    'default_code': sku,
                    'list_price': vals.get('list_price', 0),
                    'detailed_type': vals.get('detailed_type') or 'product',
                })
            else:
                product.sudo().write({
                    'name': vals.get('name') or product.name,
                    'list_price': vals.get('list_price', product.list_price),
                })

            variant = product.product_variant_ids[:1]
            if not variant:
                return {'status': 'error', 'message': 'No product variant'}

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

            if not quant:
                quant = Quant.create({
                    'product_id': variant.id,
                    'location_id': location.id,
                })

            # Check for tracking
            if variant.tracking != 'none':
                return {'status': 'error', 'message': f'Product {sku} is tracked by {variant.tracking}. Lot/Serial required.'}

            # Sets counted qty and creates stock moves (Directly apply as SUPERUSER to bypass permission/UI checks).
            from odoo import SUPERUSER_ID
            quant.with_user(SUPERUSER_ID).write({'inventory_quantity': qty})
            quant.with_user(SUPERUSER_ID)._apply_inventory()

            return {
                'status': 'success',
                'product_id': variant.id,
                'qty': qty,
                'quant': quant.id,
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

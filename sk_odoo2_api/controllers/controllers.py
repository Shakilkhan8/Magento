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
                    [('product_tmpl_id', '=', line.get('product_template_id'))], limit=1
                )
                if not product:
                    return {
                        'status': 'error',
                        'message': 'Product not found for template id: %s' % line.get('product_template_id'),
                    }
                order_lines.append((0, 0, {
                    'product_id': product.id,
                    'name': line.get('name', product.name),
                    'price_unit': line.get('price_unit', 0),
                    'product_uom_qty': line.get('product_uom_qty', 1),
                }))

            sale_order = request.env['sale.order'].sudo().create({
                'partner_id': partner.id,
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

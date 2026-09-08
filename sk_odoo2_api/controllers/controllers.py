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
            shipping_info = data.get('shipping_info', {})
            partner_info = data.get('partner_info', {})

            company_id = request.env['res.company'].sudo().search([
                ('is_api_allowed', '=', True)
            ], limit=1)

            if not company_id:
                return {
                    'status': 'error',
                    'message': 'No company configured with is_api_allowed=True on this instance.',
                }

            partner = request.env['res.partner'].sudo()
            if partner_info:
                partner = partner.create({
                    'name': partner_info.get('name', False),
                    'street': partner_info.get('street', False),
                    'street2': partner_info.get('street2', False),
                    'city': partner_info.get('city', False),
                    'zip': partner_info.get('zip', False),
                    'phone': partner_info.get('phone', False),
                    'mobile': partner_info.get('mobile', False),
                    'email': partner_info.get('email', False),
                    'vat': partner_info.get('vat', False),
                    'company_id': company_id.id,
                })

                country_name = partner_info.get('country', False)
                if country_name:
                    country = request.env['res.country'].sudo().search([
                        ('name', '=', country_name),
                    ], limit=1)

                    if not country:
                        country = request.env['res.country'].sudo().create({
                            'name': country_name,
                        })
                    partner.country_id = country.id

                state_name = partner_info.get('state', False)
                if state_name:
                    state_domain = [('name', '=', state_name)]
                    # Narrow down by country if we have one - avoids
                    # matching a same-named state in a different country
                    if partner.country_id:
                        state_domain.append(('country_id', '=', partner.country_id.id))

                    state = request.env['res.country.state'].sudo().search(state_domain, limit=1)

                    if not state:
                        state_vals = {'name': state_name}
                        if partner.country_id:
                            state_vals['country_id'] = partner.country_id.id
                            # Odoo requires a code for new states; derive a
                            # simple one if not otherwise available.
                            state_vals['code'] = (state_name[:3] or 'NA').upper()
                        state = request.env['res.country.state'].sudo().create(state_vals)

                    partner.state_id = state.id

            if not partner:
                return {'status': 'error', 'message': 'No partner found with is_biller_partner=True'}

            if not lines:
                return {'status': 'error', 'message': 'No order lines provided'}

            order_lines = []
            missing_products = []
            for line in lines:
                product_ref = line.get('product_id')
                product = request.env['product.product'].sudo().search(
                    [('id', '=', product_ref)], limit=1
                )
                if not product:
                    missing_products.append(product_ref)
                    continue

                order_lines.append((0, 0, {
                    'product_id': product.id,
                    'name': line.get('name', product.name),
                    'price_unit': line.get('price_unit', 0),
                    'product_uom_qty': line.get('product_uom_qty', 1),
                }))

            if missing_products:
                return {
                    'status': 'error',
                    'message': f'Product(s) not found for ids: {missing_products}',
                }

            if not order_lines:
                return {'status': 'error', 'message': 'No valid order lines could be built'}

            sale_order = request.env['sale.order'].sudo().create({
                'partner_id': partner.id,
                'courier_name': shipping_info.get('carrier_id', False),
                'weight': shipping_info.get('weight', False),
                'shipping_weight': shipping_info.get('shipping_weight', False),
                'move_type': shipping_info.get('move_type', False),
                'api_order_id': data.get('order_id'),
                'order_line': order_lines,
                'company_id': company_id.id,
            })

            sale_order.action_confirm()

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

        
    # @http.route('/api/create-sale-order', type='json', auth='user', csrf=False, methods=['POST'])
    # def create_sale_order_data(self, **kwargs):
    #     try:
    #         data = request.httprequest.json['params']['data']
    #         lines = data.get('lines', [])
    #         shipping_info = data.get('shipping_info', {})
    #         partner_info = data.get('partner_info', {})
    #
    #         company_id = request.env['res.company'].sudo().search([
    #             ('is_api_allowed', '=', True)
    #         ], limit=1)
    #
    #         partner = request.env['res.partner'].sudo()
    #         if partner_info:
    #             partner = partner.create({
    #                 'name': partner_info.get('name', False),
    #                 'street': partner_info.get('street', False),
    #                 'street2': partner_info.get('street2', False),
    #                 'city': partner_info.get('city', False),
    #                 'zip': partner_info.get('zip', False),
    #                 'phone': partner_info.get('phone', False),
    #                 'mobile': partner_info.get('mobile', False),
    #                 'email': partner_info.get('email', False),
    #                 'vat': partner_info.get('vat', False),
    #                 'company_id': company_id.id,
    #             })
    #
    #             country = request.env['res.country'].sudo().search([
    #                 ('name', '=', partner_info.get('country', False)),
    #             ], limit=1)
    #
    #             if country:
    #                 partner.country_id = country.id
    #             else:
    #                 country = request.env['res.country'].sudo().create({
    #                     'name': partner_info.get('country', False),
    #                 })
    #                 partner.country_id = country.id
    #
    #             state = request.env['res.country.state'].sudo().search([
    #                 ('name', '=', partner_info.get('state', False)),
    #             ])
    #
    #             if state:
    #                 partner.state_id = state.id
    #
    #             else:
    #                 state = request.env['res.country.state'].sudo().create({
    #                     'name': partner_info.get('state', False),
    #                 }, limit=1)
    #                 partner.state_id = state.id
    #
    #
    #
    #
    #         if not partner:
    #             return {'status': 'error', 'message': 'No partner found with is_biller_partner=True'}
    #
    #         if not lines:
    #             return {'status': 'error', 'message': 'No order lines provided'}
    #
    #         order_lines = []
    #         for line in lines:
    #             product = request.env['product.product'].sudo().search(
    #                 [('id', '=', line.get('product_id'))], limit=1
    #             )
    #             if not product:
    #                 return {
    #                     'status': 'error',
    #                     'message': f'Product not found for {lines}',
    #                 }
    #
    #             order_lines.append((0, 0, {
    #                 'product_id': product.id,
    #                 'name': line.get('name', product.name),
    #                 'price_unit': line.get('price_unit', 0),
    #                 'product_uom_qty': line.get('product_uom_qty', 1),
    #             }))
    #
    #         if company_id:
    #             sale_order = request.env['sale.order'].sudo().create({
    #             'partner_id': partner.id,
    #             'courier_name': shipping_info.get('carrier_id', False),
    #             'weight': shipping_info.get('weight', False),
    #             'shipping_weight': shipping_info.get('shipping_weight', False),
    #             'move_type': shipping_info.get('move_type', False),
    #             'api_order_id': data.get('order_id'),
    #             'order_line': order_lines,
    #             'company_id': company_id.id
    #             })
    #
    #             _logger.info("Sale order %s created via API", sale_order.name)
    #             return {
    #                 'status': 200,
    #                 'message': 'Sale order %s created' % sale_order.name,
    #                 'sale_order_id': sale_order.id,
    #                 'sale_order_name': sale_order.name,
    #             }
    #
    #     except Exception as e:
    #         _logger.error("Error creating sale order via API: %s", e)
    #         return {
    #             'status': 'error',
    #             'message': 'Error creating sale order: %s' % str(e),
    #         }

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
                    order.sudo().action_cancel()
                    order.sudo().state = 'cancel'

                if state == 'draft':
                    order.sudo().action_draft()
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



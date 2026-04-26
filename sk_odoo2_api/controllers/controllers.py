import base64

import requests

from odoo import http, _
from odoo.http import request
from datetime import datetime
from odoo.http import request, Response
import json

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
            # Authentication failed due to other errors
            return {
                'status': 500,
                'error': str(e),
            }

    @http.route('/api/create-sale-order', auth='user', csrf=False, methods=['POST'])
    def create_sale_order_data(self, **kwargs):
        sale_order = request.env['sale.order']

        try:
            partner_id = request.env['res.partner'].sudo().search([
                ('is_biller_partner', '=', True),
            ], limit=1)
            if not partner_id:
                response = {
                    'status': 'error',
                    'message': 'No partner found',
                }
                return http.Response(json.dumps(response), content_type='application/json')

            lines = request.httprequest.json['data']['lines']


            if lines and partner_id:
                sale_order = sale_order.create({
                    'partner_id': partner_id.id,
                    'order_line': [(0,0, {
                        'product_id': request.env['product.product'].sudo().search([('product_tmpl_id', '=', line.get('product_template_id'))], limit=1).id,
                        'name': line.get('name'),
                        'price_unit': line.get('price_unit'),
                        'product_uom_qty': line.get('product_uom_qty'),
                    }) for line in lines]
                })
                response = {
                    'status': 200,
                    'message': f'Sale order {sale_order.name} created',
                }
                return http.Response(json.dumps(response), content_type='application/json')
        except Exception as e:
            error_message = "An error occurred while creating of sale order: {}".format(e)
            response = {
                'status': 'error',
                'message': error_message
            }

            return http.Response(json.dumps(response), content_type='application/json')



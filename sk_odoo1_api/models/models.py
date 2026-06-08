import logging
import requests

from odoo import models, fields, api
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

DB = 'shakilkhan8-magento-uat-31383000'
UserName = 'api'
Password = 'admin'

BASE_URL = 'https://shakilkhan8-magento-uat-31383000.dev.odoo.com'
AUTH_URL = '/web/session/authenticate'
SALE_ORDER_URL = '/api/create-sale-order'
SALE_ORDER_UPDATE_URL = '/api/update-sale-order'

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    extra_delivery_qty = fields.Float(
        string='Extra Delivery Qty (IMR)',
        compute='_compute_extra_delivery_qty',
        store=True,
        help="Quantity that must come from IMR warehouse if other warehouses are short."
    )

    @api.depends('product_uom_qty', 'product_id', 'order_id.company_id')
    def _compute_extra_delivery_qty(self):
        imr_warehouse = self.env['stock.warehouse'].sudo().search([
            ('code', '=', 'IMR')
        ], limit=1)

        for line in self:
            if not line.product_id or line.product_id.type != 'product' or not imr_warehouse:
                line.extra_delivery_qty = 0.0
                continue

            other_warehouses = self.env['stock.warehouse'].sudo().search([
                ('id', '!=', imr_warehouse.id),
                ('company_id', '=', line.order_id.company_id.id)
            ])

            exist_qty = self.env['stock.quant'].search([
                ('warehouse_id', 'in', other_warehouses.ids),
                ('product_id', '=', line.product_id.id),
            ]).mapped('inventory_quantity_auto_apply')

            if exist_qty:
                if line.product_uom_qty > sum(exist_qty):
                    line.extra_delivery_qty = line.product_uom_qty - sum(exist_qty)
                else:
                    line.extra_delivery_qty = 0.0
            else:
                line.extra_delivery_qty = line.product_uom_qty


class SaleOrderInherit(models.Model):
    _inherit = 'sale.order'

    api_order_id = fields.Integer(
        string='API Order ID'
    )


    def action_confirm(self):
        res = super().action_confirm()

        for order in self:
            lines = order.order_line.filtered(lambda rec: rec.extra_delivery_qty > 0)
            if lines:
                api_config = self.env['api.configuration'].sudo().search([], limit=1)
                if not api_config:
                    raise ValidationError('Please create API configuration and add all API required parameters !')

                if not (api_config.url and api_config.db_name and api_config.user_name and api_config.password):
                    raise ValidationError('Please add all API required parameters !')

            if not lines:
                continue
            try:
                order._send_sale_order_to_db2(lines, params=api_config)
            except Exception as e:
                _logger.error("Failed to send sale order %s to DB2: %s", order.name, e)

        return res

    def _send_sale_order_to_db2(self, lines, params=None):


        BASE_URL = params.url
        DB = params.db_name
        UserName = params.user_name
        Password = params.password

        session = requests.Session()

        auth_response = session.post(
            BASE_URL + AUTH_URL,
            json={
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "db": DB,
                    "login": UserName,
                    "password": Password,
                }
            },
            headers={'Content-Type': 'application/json'},
            timeout=30,
        )
        auth_response.raise_for_status()
        auth_result = auth_response.json()

        if auth_result.get('error'):
            _logger.error("DB2 auth failed: %s", auth_result['error'])
            return

        order_lines = []
        for line in lines:
            tmpl_api_id = line.product_id.product_tmpl_id.api_id
            # if not tmpl_api_id:
            #     _logger.warning(
            #         "Product '%s' has no api_id, skipping line.", line.product_id.display_name
            #     )
            #     continue
            order_lines.append({
                'product_id': line.product_id.api_id,
                'product_uom_qty': line.product_uom_qty,
                'name': line.name,
                'price_unit': line.price_unit,
            })

        if not order_lines:
            _logger.warning("No valid lines to send for order %s", self.name)
            return
        token = auth_result['result']['Token_id']

        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            }

        sale_response = session.post(
            BASE_URL + SALE_ORDER_URL,
            json={
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "data": {
                        "order_id": self.id,
                        "lines": order_lines,
                    }
                }
            },
            headers=headers,
            timeout=30,
        )
        sale_response.raise_for_status()
        result = sale_response.json()

        rpc_result = result.get('result', {})
        if 'sale_order_id' in rpc_result:
            self.api_order_id = rpc_result['sale_order_id']

        _logger.info("Status", rpc_result.get('sale_order_id'))
        if rpc_result.get('status') == 200:
            _logger.info(
                "Sale order %s sent to DB2 successfully: %s",
                self.name, rpc_result.get('message'),
            )
        else:
            _logger.error("DB2 sale order creation failed: %s", rpc_result)



    def write(self, vals):
        res =  super().write(vals)
        api_config = self.env['api.configuration'].sudo().search([], limit=1)

        if not api_config:
            raise ValidationError('Please create API configuration and add all API required parameters !')

        if not (api_config.url and api_config.db_name and api_config.user_name and api_config.password):
            raise ValidationError('Please add all API required parameters !')


        if self.api_order_id:
            session = requests.Session()

            auth_response = session.post(
                BASE_URL + AUTH_URL,
                json={
                    "jsonrpc": "2.0",
                    "method": "call",
                    "params": {
                        "db": api_config.db_name,
                        "login": api_config.user_name,
                        "password": api_config.password,
                    }
                },
                headers={'Content-Type': 'application/json'},
                timeout=30,
            )

            auth_result = auth_response.json()

            token = auth_result['result']['Token_id']

            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
            }

            session.post(
                api_config.url + SALE_ORDER_UPDATE_URL,
                json={
                    "jsonrpc": "2.0",
                    "method": "call",
                        "data": {
                            "order_id": self.api_order_id,
                            "state": self.state,
                        }
                },
                headers=headers,
                timeout=30,
            )

        return res
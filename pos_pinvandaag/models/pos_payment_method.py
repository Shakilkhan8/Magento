# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
import logging
import pprint
import random
import requests
import string
import markupsafe
from werkzeug.exceptions import Forbidden

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from odoo.addons.pos_pinvandaag.const import DEFAULT_API_HOST, ALLOWED_API_HOSTS, API_ENDPOINTS

_logger = logging.getLogger(__name__)


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    def _get_payment_terminal_selection(self):
        return super(PosPaymentMethod, self)._get_payment_terminal_selection() + [('pinvandaag', 'Pin Vandaag')]

    # Pin vandaag
    pinvandaag_terminal_identifier = fields.Char(
        string="Terminal ID",
        help='The ID of the terminal',
        copy=False
    )
    pinvandaag_api_key = fields.Char(
        string="API key",
        help="The API key to use to connect with Pin Vandaag",
        copy=False
    )
    pinvandaag_api_host = fields.Selection(
        selection=[
            ('https://rest-api.pinvandaag.com/V2/', 'Primary API (rest-api.pinvandaag.com)'),
            ('https://api-backup.pinvandaag.com/V2/', 'Backup API (api-backup.pinvandaag.com)'),
        ],
        string="API host",
        help="Choose which Pin Vandaag API host should be used for this payment method",
        default=DEFAULT_API_HOST,
        required=True,
        copy=False,
    )
    pinvandaag_confirm_order_on_payment = fields.Boolean(
        string="Directly send to receipt",
        help="After payment is completed send to the receipt page",
        copy=False
    )

    @api.constrains('pinvandaag_terminal_identifier')
    def _check_pinvandaag_terminal_identifier(self):
        for payment_method in self:
            if not payment_method.pinvandaag_terminal_identifier:
                continue
            existing_payment_method = self.search(
                [
                    ('id', '!=', payment_method.id),
                    ('pinvandaag_terminal_identifier', '=',
                     payment_method.pinvandaag_terminal_identifier)
                ],
                limit=1
            )
            if existing_payment_method:
                raise ValidationError(_('Terminal %s is already used on payment method %s.')
                                      % (payment_method.pinvandaag_terminal_identifier, existing_payment_method.display_name))

    def _get_pinvandaag_api_host(self):
        self.ensure_one()
        host = self.pinvandaag_api_host or DEFAULT_API_HOST
        return host if host in ALLOWED_API_HOSTS else DEFAULT_API_HOST

    def _send_api_request(self, endpoint, payload, payment_method=None):
        payment_method = payment_method or self
        if len(payment_method) != 1:
            payment_method = payment_method[:1]
        base_url = payment_method._get_pinvandaag_api_host()
        url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        response = requests.request(
            "POST",
            url,
            data=payload,
            headers={
                "x-api-key": payment_method.pinvandaag_api_key,
            },
            timeout=60
        )
        return response

    def _pinvandaag_amount_to_pos_amount(self, amount):
        if amount in (None, False, ''):
            return None
        try:
            return float(amount) / 100.0
        except Exception:
            return None

    def _normalize_pinvandaag_receipt(self, receipt):
        if not receipt:
            return None

        # Best case: already ticket lines
        if isinstance(receipt, list):
            return json.dumps(receipt)

        # Structured dict receipt
        if isinstance(receipt, dict):
            return json.dumps(receipt)

        # Wrapped JSON string, e.g. {"customer":"[...]"}
        if isinstance(receipt, str):
            try:
                parsed = json.loads(receipt)
                if isinstance(parsed, dict) and parsed.get('customer'):
                    return parsed.get('customer')
                return receipt
            except Exception:
                return receipt

        return None

    def _normalize_pinvandaag_status_response(self, response, request_amount=None):
        transaction = response.get('transaction') or {}
        worldline = response.get('worldline') or {}
        data_node = response.get('data') or transaction or response

        status_value = (
            transaction.get('status')
            or worldline.get('status')
            or (data_node.get('status') if isinstance(data_node, dict) else None)
            or response.get('status')
        )

        if status_value == 'unknown':
            status_value = 'pending'

        amount_value = (
            transaction.get('amount')
            if transaction.get('amount') is not None
            else worldline.get('amount')
            if worldline.get('amount') is not None
            else data_node.get('amount')
            if isinstance(data_node, dict)
            else None
        )
        if amount_value is None:
            amount_value = request_amount

        return {
            'Status': status_value,
            'TransactionID': (
                transaction.get('transaction_id')
                or transaction.get('transactionId')
                or worldline.get('ssai')
                or (data_node.get('transaction_id') if isinstance(data_node, dict) else None)
                or (data_node.get('transactionId') if isinstance(data_node, dict) else None)
            ),
            'CreatedAt': (
                transaction.get('created_at')
                or transaction.get('createdAt')
                or worldline.get('lastupdate')
                or (data_node.get('created_at') if isinstance(data_node, dict) else None)
                or (data_node.get('createdAt') if isinstance(data_node, dict) else None)
            ),
            'Amount': self._pinvandaag_amount_to_pos_amount(amount_value),
            'ErrorMsg': (
                transaction.get('error_msg')
                or transaction.get('errorMsg')
                or worldline.get('errormsg')
                or (data_node.get('error_msg') if isinstance(data_node, dict) else None)
                or (data_node.get('errorMsg') if isinstance(data_node, dict) else None)
            ),
            'Receipt': self._normalize_pinvandaag_receipt(
                worldline.get('ticket')
                or transaction.get('receipt')
                or worldline.get('receipt')
                or (data_node.get('receipt') if isinstance(data_node, dict) else None)
            ),
            'paymentUrl': (
                transaction.get('payment_url')
                or (data_node.get('paymentUrl') if isinstance(data_node, dict) else None)
                or (data_node.get('payment_url') if isinstance(data_node, dict) else None)
            ),
            'resp': response,
        }

    def terminal_request(self, data, operation=False):
        # check if SaleToTerminal isset
        if 'SaleToTerminal' not in data:
            raise ValidationError(_('SaleToTerminal not set'))

        # get the terminalId
        terminal_id = data['SaleToTerminal']['TerminalID']
        # get the terminal
        terminal = self.env['pos.payment.method'].search(
            [('pinvandaag_terminal_identifier', '=', terminal_id)])
        # get the request type
        request_type = data['SaleToTerminal']['RequestType']

        # check if terminal is set
        if not terminal:
            raise ValidationError(_('Terminal not found'))
        # check if terminal has a api key
        if not terminal.pinvandaag_api_key:
            raise ValidationError(_('Terminal has no api key'))
        # check if request type is set
        if not request_type:
            raise ValidationError(_('Request type not found'))

        if data['SaleToTerminal']["RequestType"] == 'create':
            pos_amount = data['SaleToTerminal']['PaymentDetails']["Amount"]
            amount = int(pos_amount * 100)
            # create the payload
            payload = {
                'terminal_id': terminal_id,
                'amount': amount
            }
            # get the create eindpoint
            endpoint = API_ENDPOINTS['instore']['transactions']['create']
            # send the request
            response = self._send_api_request(endpoint, payload, terminal)
            # check if response is ok
            if response.status_code != 200:
                raise ValidationError(_('Response is not ok'))
            # get the response
            response = response.json()
            # check if response is ok
            if response['status'] != 'started' and response['status'] != 'pending':
                raise ValidationError(_('Response is not ok'))

            return {
                'TerminalID': terminal_id,
                'RequestType': 'create',
                'Status': 'success',
                'Response': {
                    'Status': response['status'],
                    'TransactionID': response.get('transactionId') or response.get('transaction_id'),
                    'CreatedAt': response.get('createdAt') or response.get('created_at'),
                    'Amount': pos_amount,
                }
            }
        elif data['SaleToTerminal']["RequestType"] == 'status':
            transaction_id = data['SaleToTerminal']['PaymentDetails']['TransactionId']
            if not transaction_id:
                raise ValidationError(_('Transaction id not found'))
            # create the payload
            payload = {
                'terminal_id': terminal_id,
                'transaction_id': transaction_id
            }
            # get the status eindpoint
            endpoint = API_ENDPOINTS['instore']['transactions']['status']
            # send the request
            response = self._send_api_request(endpoint, payload, terminal)
            # check if response is ok
            if response.status_code != 200:
                raise ValidationError(_('Response is not ok'))
            # get the response
            response = response.json()
            normalized = self._normalize_pinvandaag_status_response(
                response,
                request_amount=data['SaleToTerminal']['PaymentDetails'].get('Amount')
            )

            return {
                'TerminalID': terminal_id,
                'RequestType': 'status',
                'Status': 'success',
                'Response': normalized
            }
        elif data['SaleToTerminal']["RequestType"] == 'cancel':
            # create the payload
            payload = {
                'terminal_id': terminal_id,
                'transaction_id': data['SaleToTerminal']['PaymentDetails']['TransactionId'] if 'TransactionId' in data['SaleToTerminal']['PaymentDetails'] else None,
            }
            # get the cancel eindpoint
            endpoint = API_ENDPOINTS['instore']['terminal']['cancel']
            # send the request
            response = self._send_api_request(endpoint, payload, terminal)
            # check if response is ok
            if response.status_code != 200:
                raise ValidationError(_('Response is not ok'))
            # get the response
            response = response.json()
            if response.get('status') not in ('success', 'stopped'):
                raise ValidationError(_('Response is not ok'))
            return {
                'TerminalId': terminal_id,
                'RequestType': 'cancel',
                'Status': 'success',
            }
        elif data['SaleToTerminal']["RequestType"] == 'getLastTransaction':
            # create the payload
            payload = {
                'terminal_id': terminal_id,
            }
            endpoint = API_ENDPOINTS['instore']['transactions']['getLatestTransaction']
            response = self._send_api_request(endpoint, payload, terminal)
            # check if response is ok
            if response.status_code != 200:
                raise ValidationError(_('Response is not ok'))
            # get the response
            response = response.json()
            normalized = self._normalize_pinvandaag_status_response(response)

            return {
                'TerminalId': terminal_id,
                'RequestType': 'getLastTransaction',
                'Status': 'success',
                'Response': normalized
            }
        elif data['SaleToTerminal']["RequestType"] == 'refund':
            # create the payload
            # Check if amount is set
            if 'Amount' not in data['SaleToTerminal']['PaymentDetails']:
                raise ValidationError(_('Amount not set'))
            amount = int(abs(float(data['SaleToTerminal']['PaymentDetails']['Amount'])) * 100)
            payload = {
                'terminal_id': terminal_id,
                'amount': amount,
            }
            endpoint = API_ENDPOINTS['instore']['transactions']['refund']
            response = self._send_api_request(endpoint, payload, terminal)
            # check if response is ok
            if response.status_code != 200:
                raise ValidationError(_('Response is not ok'))
            # get the response
            response = response.json()
            if response['status'] not in ('started', 'pending'):
                raise ValidationError(_('Response is not ok'))

            return {
                'TerminalId': terminal_id,
                'RequestType': 'refund',
                'Status': 'success',
                'Response': {
                    'Status': response['status'],
                    'TransactionID': response.get('transactionId') or response.get('transaction_id'),
                    'CreatedAt': response.get('createdAt') or response.get('created_at'),
                    'Amount': abs(float(data['SaleToTerminal']['PaymentDetails']['Amount'])),
                    'resp': response
                }
            }

# Part of Odoo. See LICENSE file for full copyright and licensing details.

# API hosts
DEFAULT_API_HOST = 'https://rest-api.pinvandaag.com/V2/'
ALLOWED_API_HOSTS = {
    'https://rest-api.pinvandaag.com/V2/',
    'https://api-backup.pinvandaag.com/V2/',
}

API_ENDPOINTS = dict({
    'instore': {
        'transactions': {
            'create': 'instore/transactions/start',
            'status': 'instore/transactions/status',
            'mailreceipt': 'instore/transactions/mailreceipt',
            'date': 'instore/transactions/date',
            'refund': 'instore/transactions/refund',
            'getLatestTransaction': 'instore/transactions/last_transaction',
        },
        'terminal': {
            'status': 'instore/terminal/status',
            'ctmp': 'instore/terminal/ctmp',
            'cancel': 'instore/transactions/stop',
        },
    },
})

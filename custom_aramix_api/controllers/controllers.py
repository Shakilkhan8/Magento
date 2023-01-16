# -*- coding: utf-8 -*-
# from odoo import http


# class CustomAramixApi(http.Controller):
#     @http.route('/custom_aramix_api/custom_aramix_api', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_aramix_api/custom_aramix_api/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_aramix_api.listing', {
#             'root': '/custom_aramix_api/custom_aramix_api',
#             'objects': http.request.env['custom_aramix_api.custom_aramix_api'].search([]),
#         })

#     @http.route('/custom_aramix_api/custom_aramix_api/objects/<model("custom_aramix_api.custom_aramix_api"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_aramix_api.object', {
#             'object': obj
#         })

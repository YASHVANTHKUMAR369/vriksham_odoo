# -*- coding: utf-8 -*-
# from odoo import http


# class PayrollIcore(http.Controller):
#     @http.route('/payroll_icore/payroll_icore', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/payroll_icore/payroll_icore/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('payroll_icore.listing', {
#             'root': '/payroll_icore/payroll_icore',
#             'objects': http.request.env['payroll_icore.payroll_icore'].search([]),
#         })

#     @http.route('/payroll_icore/payroll_icore/objects/<model("payroll_icore.payroll_icore"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('payroll_icore.object', {
#             'object': obj
#         })


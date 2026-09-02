# -*- coding: utf-8 -*-
import json
import logging
from xmlrpc import client as xmlrpc_client

from markupsafe import Markup

from odoo import fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class InvoiceXmlrpcDashboard(models.Model):
    _name = 'invoice.xmlrpc.dashboard'
    _description = 'Invoice XML-RPC Dashboard'
    _order = 'id desc'

    name = fields.Char(
        string='Invoice Number', required=True,
        help="Value of the 'name' field on the remote invoice (account.move), "
             "e.g. INV/25-26/146",
    )
    state = fields.Selection(
        [('draft', 'Draft'), ('fetched', 'Fetched')],
        default='draft', readonly=True,
    )
    raw_data = fields.Text(string='Fetched JSON Data', readonly=True)
    company_logo = fields.Binary(string='Remote Company Logo', readonly=True, attachment=True)

    # ------------------------------------------------------------------
    # Fetch
    # ------------------------------------------------------------------
    def _get_connection_parameters(self):
        icp = self.env['ir.config_parameter'].sudo()
        url = icp.get_param('xmlrpc_invoice_dashboard.odoo_url')
        db = icp.get_param('xmlrpc_invoice_dashboard.odoo_db')
        username = icp.get_param('xmlrpc_invoice_dashboard.odoo_username')
        password = icp.get_param('xmlrpc_invoice_dashboard.odoo_password')
        if not all([url, db, username, password]):
            raise UserError(_(
                "Please configure the Odoo URL, Database, Username and Password "
                "under Invoice XML-RPC > Configuration > Settings before fetching data."
            ))
        return url.rstrip('/'), db, username, password

    @staticmethod
    def _existing_fields(models_proxy, db, uid, password, model, candidates):
        available = models_proxy.execute_kw(db, uid, password, model, 'fields_get', [], {'attributes': []})
        return [field for field in candidates if field in available]

    def action_fetch_data(self):
        self.ensure_one()
        if not self.name:
            raise UserError(_("Please enter an invoice number first."))

        url, db, username, password = self._get_connection_parameters()

        try:
            common = xmlrpc_client.ServerProxy('%s/xmlrpc/2/common' % url)
            uid = common.authenticate(db, username, password, {})
        except Exception as exc:
            _logger.exception("XML-RPC authentication to %s failed", url)
            raise UserError(_("Could not connect to %(url)s: %(error)s", url=url, error=exc))

        if not uid:
            raise UserError(_(
                "Authentication failed for user '%(user)s' on database '%(db)s'. "
                "Please check the credentials in Settings.", user=username, db=db,
            ))

        models_proxy = xmlrpc_client.ServerProxy('%s/xmlrpc/2/object' % url)

        def execute(model, method, *args, **kwargs):
            try:
                return models_proxy.execute_kw(db, uid, password, model, method, list(args), kwargs)
            except xmlrpc_client.Fault as exc:
                raise UserError(_("The remote Odoo server returned an error: %s", exc.faultString))
            except Exception as exc:
                raise UserError(_("Could not reach the remote Odoo server: %s", exc))

        move_fields = self._existing_fields(models_proxy, db, uid, password, 'account.move', [
            'name', 'invoice_date', 'invoice_date_due', 'ref', 'move_type', 'narration',
            'amount_untaxed', 'amount_tax', 'amount_total', 'amount_total_words', 'tax_totals',
            'partner_id', 'company_id', 'invoice_line_ids', 'partner_bank_id', 'currency_id',
            'x_bill_date',
        ])
        moves = execute(
            'account.move', 'search_read',
            [('name', '=', self.name), ('move_type', 'in', ('out_invoice', 'out_refund'))],
            fields=move_fields, limit=1,
        )
        if not moves:
            raise UserError(_("No invoice found on the remote server with number '%s'.", self.name))
        move = moves[0]

        partner_info = {}
        if move.get('partner_id'):
            partner_fields = self._existing_fields(models_proxy, db, uid, password, 'res.partner', [
                'name', 'street', 'street2', 'city', 'zip', 'state_id', 'country_id',
                'vat', 'phone', 'email', 'l10n_in_pan',
            ])
            partners = execute('res.partner', 'read', [move['partner_id'][0]], fields=partner_fields)
            if partners:
                partner_info = partners[0]

        company_info = {}
        logo_data = False
        if move.get('company_id'):
            company_fields = self._existing_fields(models_proxy, db, uid, password, 'res.company', [
                'name', 'street', 'street2', 'city', 'zip', 'state_id', 'country_id',
                'vat', 'phone', 'email', 'l10n_in_pan', 'logo',
            ])
            companies = execute('res.company', 'read', [move['company_id'][0]], fields=company_fields)
            if companies:
                company_info = companies[0]
                logo_data = company_info.pop('logo', False)

        lines = []
        if move.get('invoice_line_ids'):
            line_fields = self._existing_fields(models_proxy, db, uid, password, 'account.move.line', [
                'name', 'quantity', 'price_unit', 'price_subtotal', 'display_type', 'l10n_in_hsn_code',
            ])
            move_lines = execute('account.move.line', 'read', move['invoice_line_ids'], fields=line_fields)
            lines = [line for line in move_lines if line.get('display_type') == 'product']

        bank_info = {}
        if move.get('partner_bank_id'):
            bank_fields = self._existing_fields(models_proxy, db, uid, password, 'res.partner.bank', [
                'acc_number', 'bank_id', 'partner_id',
            ])
            banks = execute('res.partner.bank', 'read', [move['partner_bank_id'][0]], fields=bank_fields)
            if banks:
                bank_info = banks[0]
                if bank_info.get('bank_id'):
                    res_bank_fields = self._existing_fields(
                        models_proxy, db, uid, password, 'res.bank', ['name', 'city', 'bic'])
                    res_banks = execute('res.bank', 'read', [bank_info['bank_id'][0]], fields=res_bank_fields)
                    bank_info['bank'] = res_banks[0] if res_banks else {}
                if bank_info.get('partner_id'):
                    bank_info['beneficiary_name'] = bank_info['partner_id'][1]

        data = {
            'invoice': move,
            'partner': partner_info,
            'company': company_info,
            'lines': lines,
            'bank': bank_info,
        }

        self.write({
            'raw_data': json.dumps(data, indent=2, ensure_ascii=False, default=str),
            'state': 'fetched',
            'company_logo': logo_data,
        })
        return True

    def action_print_pdf(self):
        self.ensure_one()
        if not self.raw_data:
            raise UserError(_("Please fetch the invoice data before printing."))
        return self.env.ref('xmlrpc_invoice_dashboard.action_report_invoice_xmlrpc').report_action(self)

    # ------------------------------------------------------------------
    # Report helpers (called from the QWeb template)
    # ------------------------------------------------------------------
    def _data(self):
        self.ensure_one()
        try:
            return json.loads(self.raw_data) if self.raw_data else {}
        except ValueError:
            return {}

    def _invoice(self):
        return self._data().get('invoice') or {}

    def _partner(self):
        return self._data().get('partner') or {}

    def _company(self):
        return self._data().get('company') or {}

    def _lines(self):
        return self._data().get('lines') or []

    def _bank(self):
        return self._data().get('bank') or {}

    def _tax_totals(self):
        return self._invoice().get('tax_totals') or {}

    def _tax_groups(self):
        subtotals = self._tax_totals().get('subtotals') or []
        return subtotals[0].get('tax_groups', []) if subtotals else []

    @staticmethod
    def _m2o_name(value):
        return value[1] if value else ''

    def _address_lines(self, info):
        if not info:
            return []
        lines = []
        if info.get('street'):
            lines.append(info['street'])
        if info.get('street2'):
            lines.append(info['street2'])
        city_zip = ' '.join(part for part in [info.get('city'), info.get('zip')] if part)
        if city_zip:
            lines.append(city_zip)
        state = self._m2o_name(info.get('state_id'))
        if state:
            lines.append(state)
        country = self._m2o_name(info.get('country_id'))
        if country:
            lines.append(country)
        return lines

    def _partner_address_lines(self):
        return self._address_lines(self._partner())

    def _company_address_lines(self):
        return self._address_lines(self._company())

    def _formatted_date(self, key):
        value = self._invoice().get(key)
        if not value:
            return ''
        try:
            return fields.Date.from_string(value.split(' ')[0]).strftime('%d/%m/%Y')
        except (ValueError, TypeError):
            return value

    def _billing_month(self):
        value = self._invoice().get('x_bill_date')
        if not value:
            return ''
        try:
            return fields.Date.from_string(value.split(' ')[0]).strftime('%B %Y')
        except (ValueError, TypeError):
            return value

    def _narration_html(self):
        value = self._invoice().get('narration') or ''
        return Markup(value)

    @staticmethod
    def _fmt_amount(amount):
        try:
            amount = float(amount or 0.0)
        except (TypeError, ValueError):
            return amount
        negative = amount < 0
        amount = abs(amount)
        whole, _dot, decimals = f"{amount:.2f}".partition('.')
        if len(whole) > 3:
            last3 = whole[-3:]
            rest = whole[:-3]
            groups = []
            while len(rest) > 2:
                groups.insert(0, rest[-2:])
                rest = rest[:-2]
            if rest:
                groups.insert(0, rest)
            whole = ','.join(groups) + ',' + last3
        return "₹ %s%s.%s" % ('-' if negative else '', whole, decimals)

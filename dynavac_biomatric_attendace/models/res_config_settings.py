import datetime
from datetime import date

import requests
from odoo import fields, models, api
import logging
_logger = logging.getLogger(__name__)


class BiometricSettings(models.TransientModel):
    """Inherit the model to add fields"""
    _inherit = 'res.config.settings'

    biometric_api_url = fields.Char(string="Biometric API URL", readonly=False,
                                    config_parameter='dynavac_biomatric_attendace.biometric_api_url')
    from_date = fields.Datetime(string="From Date", readonly=False,
                                    config_parameter='dynavac_biomatric_attendace.from_date')
    to_date = fields.Datetime(string="To Date", readonly=False,
                                    config_parameter='dynavac_biomatric_attendace.to_date')

    def set_values(self):
        """Set values,
         Returns:
        :return: The result of the superclasses' set_values method.
        """
        res = super(BiometricSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param(
            'biometric_api_url', self.biometric_api_url)
        self.env['ir.config_parameter'].sudo().set_param(
            'from_date', self.from_date)
        self.env['ir.config_parameter'].sudo().set_param(
            'to_date', self.to_date)
        return res


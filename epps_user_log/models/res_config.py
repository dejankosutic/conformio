# -*- coding: utf-8 -*-
##############################################################################
# This software is © copyright 2016 EPPS Services Ltd and licensed under the
# GNU Affero General Public License, version 3.0 as published by the Free
# Software Foundation.
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################


from openerp import fields, models, api


class BaseConfigSettings(models.TransientModel):
    _inherit = 'base.config.settings'

    ip_logging_enabled = fields.Boolean(
        string="IP Logging Enabled",)

    @api.model
    def get_default_ip_logging_enabled(self, fields):
        icp = self.env['ir.config_parameter']
        ip_logging_enabled_param = icp.get_param('ip_logging_enabled')
        ip_logging_enabled = ip_logging_enabled_param == 'True' and True or False
        return {'ip_logging_enabled': ip_logging_enabled}

    @api.multi
    def set_ip_logging_enabled(self):
        icp = self.env['ir.config_parameter']
        icp.set_param('ip_logging_enabled', str(self.ip_logging_enabled))


# -*- coding: utf-8 -*-
##############################################################################
# This software is © copyright 2016 EPPS Services Ltd and licensed under the
# GNU Affero General Public License, version 3.0 as published by the Free
# Software Foundation.
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################

from openerp import models, fields, api


class ResPartner(models.Model):
    """Extends Partner model with new fields"""
    _inherit = 'res.partner'

    @api.one
    def get_formview_id(self):
        view_id = self.env['ir.model.data'].get_object_reference(
            'epps_partner', 'epps_view_partner_form')
        view_id = view_id and view_id[1] or False
        if view_id:
            return view_id
        return False

    admin_firstname = fields.Char("First name", required=True, default='')
    admin_lastname  = fields.Char("Last name", required=True, default='')
    subdomain_name = fields.Char('Subdomain name', readonly=True)
    country_id = fields.Many2one('res.country', 'Country', required=True)
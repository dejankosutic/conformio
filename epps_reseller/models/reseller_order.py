# -*- coding: utf-8 -*-
##############################################################################
# This software is © copyright 2016 EPPS Services Ltd and licensed under the
# GNU Affero General Public License, version 3.0 as published by the Free
# Software Foundation.
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################

from openerp import models, fields, api
from unidecode import unidecode
import string
import requests
#import json

""""
class ProductTemplate(models.Model):
    _inherit = "product.template"

    type = fields.Selection(
        selection_add=[('odoo_pack', 'Odoo Pack')]
    )
"""

class ResellerOrder(models.Model):
    """Reseller Order management"""
    _name = 'reseller.order'

    name = fields.Char('Order number',
                       default='/',
                       readonly=True,
                       required=True
                       )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Customer',
    )
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Please select the plan',
        required=True,
        domain=[('type', 'in', ('consu','odoo_pack'))],
    )
    product_code = fields.Char(
        string='Package product code',
        compute='_compute_product_code',
        store=False,
        copy=False,
        readonly=True,
    )
    product_plan_toolkit_id = fields.Many2one(
        comodel_name='product.product',
        string='Select the toolkit included in the plan',
        domain=[('type', 'in', ('consu','odoo_pack'))],
    )
    product_toolkit_id = fields.Many2one(
        comodel_name='product.product',
        string='Select additional toolkit',
        domain=[('type', 'in', ('consu','odoo_pack'))],
    )

    order_date = fields.Date(string='Order date')
    canceled_date = fields.Date(string='Canceled date')
    state = fields.Selection(
        selection=[('draft', 'Processing'),
                   ('active', 'Active'),
                   ('canceled', 'Canceled')],
        default='draft'
    )
    subdomain_name = fields.Char('Subdomain name', compute='_compute_subdomain_name')

    first_name = fields.Char('First name',compute='_compute_name')
    last_name = fields.Char('Last name',compute='_compute_name')

    @api.onchange('product_id')
    def _get_plan_toolkits(self):
        # First empty the field
        self.product_plan_toolkit_id = False
        self.product_toolkit_id = False

        selected_products = []
        for prod in self.product_id.product_link_ids:
            if not prod.linked_product_id.material_type == 'L' and prod.type != 'included':
                selected_products.append(prod.linked_product_id.id)
        print selected_products
        # Adds a custom domain to the desired field
        return {'domain': {'product_plan_toolkit_id': [('id', 'in', selected_products)]}}

    @api.one
    @api.depends('product_id')
    def _compute_product_code(self):
        if self.product_id:
            self.product_code = self.product_id.default_code

    @api.one
    @api.depends('partner_id')
    def _compute_name(self):
        if self.partner_id:
            first_name = self.partner_id.admin_firstname
            last_name = self.partner_id.admin_lastname
            self.first_name = first_name
            self.last_name = last_name

    @api.one
    @api.depends('partner_id')
    def _compute_subdomain_name(self):
        if self.partner_id:
            def strip_string_and_lowercase(s):
                sa = unidecode(s).lower().replace(' ', '_')
                # this will "eat" chars sa = s.encode('ascii', 'ignore').lower()
                allowed = string.ascii_lowercase + string.digits + '_'
                return ''.join(c for c in sa if c in allowed)
            #first_name = self.partner_id.admin_firstname
            #last_name = self.partner_id.admin_lastname
            config_param = self.env['ir.config_parameter']
            subdomain_sufix = config_param.get_param('epps.subdomain_sufix')
            if subdomain_sufix:
                name = self.partner_id.name
                subdomain_name = strip_string_and_lowercase(str(name)) + str(subdomain_sufix)
                self.subdomain_name = 'https://' + subdomain_name

    @api.model
    def create(self, vals=None):
        """ Automatic Order number using sequence"""
        if vals.get('name', '/') == '/':
            vals['name'] = self.env[
                'ir.sequence'].next_by_code('reseller.order')
        # TODO call curl provisioning that will write date and state after
        # provisioning
        vals['order_date'] = fields.Date.context_today(self)
        vals['state'] = 'active'

        res = super(ResellerOrder, self).create(vals)
        res._call_provisioning()
        return res

    @api.multi
    def _call_provisioning(self):
        """ Cals provisioning service """
        self.ensure_one()
        config_proxy = self.env['ir.config_parameter']
        url = config_proxy.get_param('epps.prov_service')

        reseller_id = config_proxy.get_param('epps.prov_partner_id')
        reseller_database_id = config_proxy.get_param('epps.prov_database_id')

        payload = {#'name': self.partner_id.name,
            'email': self.partner_id.email,
            'country': self.partner_id.country_id.name,
            'reseller_id': reseller_id,
            'reseller_database_id': reseller_database_id,
            'name': self.partner_id.admin_firstname,  # TODO remove
            'company': self.partner_id.name,
            'firstname': self.partner_id.admin_firstname,
            'lastname': self.partner_id.admin_lastname,
            'productId': self.product_id.default_code,
            'product_plan_toolkit_id': self.product_plan_toolkit_id.default_code,
            'product_toolkit_id': self.product_toolkit_id.default_code,
            'client_order_ref': self.name,
            'country': self.partner_id.country_id and self.partner_id.country_id.code or False,
            'zip': self.partner_id.zip,
            'address1': self.partner_id.street,
            'address2': self.partner_id.street2,
            'city': self.partner_id.city,
            'workPhone': self.partner_id.phone,
            'mobilePhone': self.partner_id.mobile,
            'is_company': self.partner_id.is_company or True, #This needs to be true so the name does not split.
        }
        r = requests.post(url, data=payload)

# -*- coding: utf-8 -*-
##############################################################################
# This software is © copyright 2016 EPPS Services Ltd and licensed under the
# GNU Affero General Public License, version 3.0 as published by the Free
# Software Foundation.
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################

from openerp import models, fields, api, _
from openerp.exceptions import Warning


class EppsAccountSettings(models.TransientModel):
    _name = 'epps.account.settings'

    @api.one
    @api.depends('additional_users')
    def _get_num_of_users(self):
        company = self.env['res.company'].search([], limit=1)[0]
        if not company:
            self.max_number_of_users = 0
            self.number_of_users = 0
        if company:
            self.max_number_of_users = company.max_number_of_users
            self.number_of_users = company.number_of_users
            self.remaining_users = company.remaining_users

    @api.one
    @api.depends('additional_users')
    def _get_num_of_gb(self):
        #company = self.env['res.company'].search([], limit=1)[0]
        company = self.env.user.company_id
        if not company:
            self.max_space_gb = 0
        if company:
            self.max_space_gb = company.max_space_gb

    additional_users = fields.Integer('Additional users')
    additional_storage = fields.Integer('Additional storage space (GB)')
    features_table_html = fields.Text(
        'HTML',
        compute='_features_table_html',
        readonly=True,
        translate=True)
    max_number_of_users = fields.Integer(
        string='Max',
        compute='_get_num_of_users',
        )
    number_of_users = fields.Integer(
        string='Users',
        compute='_get_num_of_users',
        )
    remaining_users = fields.Integer(
        string='Remaining',
        compute='_get_num_of_users',
    )
    max_space_gb = fields.Integer(
        string='Max GB',
        compute='_get_num_of_gb',
        )

    @api.multi
    def remove_users(self):
        self.ensure_one() 
        if self.additional_users > 0:
            self.additional_users -= 1
        else:
            raise Warning(_("Please enter a number between 0 and 100"))

    @api.multi
    def add_users(self):
        self.ensure_one()
        if self.additional_users < 100:
            self.additional_users += 1
        else:
            raise Warning(_("Please enter a number between 0 and 100"))

    @api.multi
    def remove_storage(self):
        self.ensure_one()
        if self.additional_storage > 0:
            self.additional_storage -= 1
        else:
            raise Warning(_("Please enter a number between 0 and 100"))

    @api.multi
    def add_storage(self):
        self.ensure_one()
        if self.additional_storage < 100:
            self.additional_storage += 1
        else:
            raise Warning(_("Please enter a number between 0 and 100"))

    @api.multi
    def purchase_users(self):
        self.ensure_one()
        _generated_url = ""
        if self.additional_users > 0:
            default_url_obj = self.env['ir.config_parameter'].get_param('epps.bluesnap_url')
            product_obj = self.env['product.product'].search([('default_code','=','U1')])
            if default_url_obj and product_obj:
                #product_code = product_obj['default_code'] or ''
                product_bluesnap_code = product_obj['bluesnap_code'] or ''
                _generated_url = _generated_url + default_url_obj + '?' + product_bluesnap_code + '=' + str(self.additional_users)
            else:
                raise Warning('Something went wrong.')
        if _generated_url:
            return{ 'type': 'ir.actions.act_url', 'url': _generated_url, 'target':'new'}
        else:
            return False

    @api.multi
    def purchase_storage(self):
        self.ensure_one()
        _generated_url = ""
        if self.additional_storage > 0:
            default_url_obj = self.env['ir.config_parameter'].get_param('epps.bluesnap_url')
            product_obj = self.env['product.product'].search([('default_code','=','G1')])
            if default_url_obj and product_obj:
                #product_code = product_obj['default_code'] or ''
                product_bluesnap_code = product_obj['bluesnap_code'] or ''
                _generated_url = default_url_obj + '?' + product_bluesnap_code + '=' + str(self.additional_storage)
            else:
                raise Warning('Something went wrong.')
        if _generated_url:
            return{ 'type': 'ir.actions.act_url', 'url': _generated_url, 'target':'new'}
        else:
            return False

    @api.one
    @api.depends('additional_users')
    def _features_table_html(self):
        html = ''

        company_obj = self.env['res.company'].search([], limit=1)[0]
        current_plan = company_obj.plan_product_id.default_code
        default_url_obj = self.env['ir.config_parameter'].get_param('epps.bluesnap_url')
        plan_1_url_obj = self.env['ir.config_parameter'].get_param('epps.plan_1_upgrade_url')
        plan_2_url_obj = self.env['ir.config_parameter'].get_param('epps.plan_2_upgrade_url')
        plan_3_url_obj = self.env['ir.config_parameter'].get_param('epps.plan_3_upgrade_url')
        plan_4_url_obj = self.env['ir.config_parameter'].get_param('epps.plan_4_upgrade_url')

        default_support_url_obj = self.env['ir.config_parameter'].get_param('epps.account_settings_support_url')
        prod_obj_all = self.env['product.product'].search([])

        if prod_obj_all:
            table_rows = []
            table_columns = []
            temp = {}
            """
            for product in prod_obj_all:
                if product.product_link_ids:
                    table_columns.append(product)
                    temp[product] = []
                    for product_link in product.product_link_ids:
                        temp[product].append(product_link.linked_product_id)
                        if product_link.linked_product_id in table_rows:
                            pass
                        else:
                            table_rows.append(product_link.linked_product_id)
            """
            max_row_count = 0
            for product in prod_obj_all:
                if product.material_type == 'L' and product.description:
                    table_columns.append(product)
                    temp[product] = []
                    description_list = []
                    if product.description:
                        description_list = product.description.split(';')
                        if len(description_list) > max_row_count:
                            max_row_count = len(description_list)
                    for product_link in description_list:
                        temp[product].append(product_link)
                        if product_link in table_rows:
                            pass
                        else:
                            table_rows.append(product_link)

            if table_columns and table_rows:
                html ="<div class='plan_settings'><table>"
                #html += "<tr><th></th>"
                html += "<tr>"
                for c in table_columns[:-1]:
                    html += "<th>" + str(c.name) + "</th>"
                html += "<th class='last_column_td'>"+table_columns[-1].name+"</th></tr>"


                for a in range(0, max_row_count):
                    #html += '<tr><td class="align_left_td">' + str(a) + '</td>'
                    html += '<tr>'
                    for key in table_columns:
                        if key in temp:
                            if len(temp[key]) > a:
                                html += "<td class=''>" + str(temp[key][a] or '') + "</td>"
                            else:
                                html +="<td></td>"
                        else:
                            html += "<td></td>"

                    html +='<tr class="last_row_tr">'

                #html +="<td></td>"
                for c in table_columns:
                    if c.default_code and c.bluesnap_code and default_support_url_obj and company_obj.plan_product_id:
                        _generated_support_url = ""
                        _generated_support_url = default_support_url_obj
                        if c.default_code > current_plan:
                            if current_plan == 'L0':
                                if c.default_code == 'L1':
                                    if plan_1_url_obj:
                                        html += '<td><a target="_tab" href="' + plan_1_url_obj + '" class="oe_highlight_upgrade">UPGRADE</a></td>'
                                    else:
                                        html += "<td></td>"
                                elif c.default_code == 'L2':
                                    if plan_2_url_obj:
                                        html += '<td><a target="_tab" href="' + plan_2_url_obj + '" class="oe_highlight_upgrade">UPGRADE</a></td>'
                                    else:
                                        html += "<td></td>"
                                elif c.default_code == 'L3':
                                    if plan_3_url_obj:
                                        html += '<td><a target="_tab" href="' + plan_3_url_obj + '" class="oe_highlight_upgrade">UPGRADE</a></td>'
                                    else:
                                        html += "<td></td>"
                                elif c.default_code == 'L4':
                                    if plan_4_url_obj:
                                        html += '<td><a target="_tab" href="' + plan_4_url_obj + '" class="oe_highlight_upgrade">UPGRADE</a></td>'
                                    else:
                                        html += "<td></td>"
                                else:
                                    html += '<td><a target="_tab" href="' + _generated_support_url + '" class="oe_highlight_upgrade">UPGRADE</a></td>'
                            else:
                                html += '<td><a target="_tab" href="' + _generated_support_url + '" class="oe_highlight_upgrade">UPGRADE</a></td>'
                        elif c.default_code < current_plan:
                            #For now does nothing
                            if c.default_code == 'L0':
                                html += '<td><a target="_tab" href="' + _generated_support_url + '" class="oe_highlight_gray_button">DOWNGRADE</a></td>'
                            else:
                                html += '<td><a target="_tab" href="' + _generated_support_url + '" class="oe_highlight_gray_button">DOWNGRADE</a></td>'
                        elif c.default_code == current_plan:
                            html += '<td><a href="#" class="oe_gray_button">Current plan</a></td>'
                    else:
                        html +="<td></td>"
                html += "</tr>"
    
                html +="</table></div>"

        self.features_table_html = html

class ProductTemplate(models.Model):
    _inherit = "product.template"

    # default_code is used to identify product, except when from BlueSnap
    bluesnap_code = fields.Char("BlueSnap Code")
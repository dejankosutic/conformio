# -*- coding: utf-8 -*-
##############################################################################
# This software is © copyright 2016 EPPS Services Ltd and licensed under the
# GNU Affero General Public License, version 3.0 as published by the Free
# Software Foundation.
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################

from openerp import models, fields, api, _, SUPERUSER_ID
from openerp.exceptions import Warning


class update_logo_name_wizard(models.TransientModel):
    _name = 'update.logo.name.wizard'

    def _get_default_company_name(self):
        return self.env.user.company_id.name or ''

    name = fields.Char('Organization Name', default=lambda self: self._get_default_company_name())
    logo = fields.Binary('Logo',)

    @api.model
    def action_update_logo_name(self):
        dwa = self.env['dwa.fields']
        mod_obj = self.env['ir.model.data']
        act_obj = self.pool.get('ir.actions.act_window')
        # get logo and name from dwa by xml
        logo_ref = mod_obj.get_object_reference('epps_design',
                                                'epps_dwa_fields_company_logo')
        name_ref = mod_obj.get_object_reference('epps_design',
                                                 'epps_dwa_fields_organization_name')
        logo_id = logo_ref and [logo_ref[1]] or False
        name_id = name_ref and [name_ref[1]] or False
        logo_value = dwa.browse(logo_id).value
        name_value = dwa.browse(name_id).value
        # force wizard if there are default values in dwa
        if logo_value == 'Company logo' and name_value == 'Organization name':
            wizard_id = self.create({})
            # 3get wizard action and update res_id with wizard created
            result = mod_obj.get_object_reference('epps_company_rules', 'action_update_logo_name_wizard')
            id = result and result[1] or False
            result = act_obj.read(self._cr, self._uid, [id], context=self._context)[0]
            result['res_id'] = wizard_id.id
            return result
        else:
            # if not default values return company rules action
            result = mod_obj.get_object_reference('epps_company_rules', 'epps_company_rules_project_action')
            id = result and result[1] or False
            result = act_obj.read(self._cr, self._uid, [id], context=self._context)[0]
            return result

    @api.multi
    def submit(self):
        dwa = self.env['dwa.fields']
        mod_obj = self.env['ir.model.data']
        act_obj = self.pool.get('ir.actions.act_window')
        # get logo and name from dwa by xml
        logo_ref = mod_obj.get_object_reference('epps_design',
                                                'epps_dwa_fields_company_logo')
        name_ref = mod_obj.get_object_reference('epps_design',
                                                 'epps_dwa_fields_organization_name')
        logo_id = logo_ref and [logo_ref[1]] or False
        name_id = name_ref and [name_ref[1]] or False

        logo = dwa.browse(logo_id)
        name = dwa.browse(name_id)
        print ('logo_id')
        print (logo_id)
        print (name_id)
        print (logo_ref)
        print (name_ref)


        customer_admin_obj = self.env.ref("base.user_customer_administrator") or False
        if self._uid != customer_admin_obj.id:
            raise Warning(_('Please ask your administrator to complete the initial setup first.'))
        elif not self.name:
            raise Warning(_('Organization name must not be empty.'))
        elif not logo.ir_att_id:
            raise Warning(_('You must pick a logo.'))
        # elif not self.logo:
        #     raise Warning(_('You must pick a logo.'))
        else:
            # update logo and name with values from wizard

            # logo is updated on upload
            #logo.sudo().write({'logo': self.logo})

            #get company rules project id
            company_rules_ref = mod_obj.get_object_reference('epps_company_rules',
                                                'epps_company_rules_project')
            company_rules_id = company_rules_ref and company_rules_ref[1] or False
            #get company rules directory id
            #company_rules_directory = self.env['document.directory'].search([('ressource_id', '=', company_rules_id)], limit=1)
            #company_rules_directory_id = company_rules_directory.id
            company_rules_directory_id = self.env['ir.attachment'].get_dwa_root_folder()
            ctx = self._context.copy()
            ctx.update({'company_rules_id': company_rules_id})
            #create a new ir attachment containing organizations logo
            # ir_att_id = self.env['ir.attachment'].with_context(ctx).insert_new_attachment(company_rules_directory_id,
            #                                                             'organization_logo',
            #                                                             logo.logo)
            # if ir_att_id:
            #     logo.sudo().write({'ir_att_id': ir_att_id})
            name.sudo().write({'value': self.name})
            # get users company, and update name and logo
            company = self.env['res.users'].browse(self._uid).company_id
            company.sudo().write({'name': self.name,
                                  # 'logo': self.logo
                                  })

            # Copy from repo (this is not done in provisioning)
            #self.env['ir.attachment'].copy_repo_2_dwa()
            # Compile the docx files
            self.env['ir.attachment'].apply_dwa_2_dwa_folder()
            # return company rules view
            result = mod_obj.get_object_reference('epps_company_rules', 'epps_company_rules_project_action')
            id = result and result[1] or False
            result = act_obj.read(self._cr, self._uid, [id], context=self._context)[0]
            return result
        return False


class IrAttachment(models.Model):
    _inherit = 'ir.attachment',

    def prepare_attachment_vals(self, cr, uid, fid, name, data, context=None):
        vals = super(IrAttachment, self).prepare_attachment_vals(cr, uid, fid, name, data, context=context)
        company_rules_id = context.get('company_rules_id', False)
        if company_rules_id:
            vals.update( {'datas_fname': 'organization_logo.png',
                          'res_id': company_rules_id,
                          'res_model': 'project.project',
                          'index_content': 'image',
                         })
        return vals
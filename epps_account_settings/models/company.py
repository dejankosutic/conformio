# -*- coding: utf-8 -*-
##############################################################################
# This software is © copyright 2016 EPPS Services Ltd and licensed under the
# GNU Affero General Public License, version 3.0 as published by the Free
# Software Foundation.
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################

from openerp import models, fields, api


class ResCompany(models.Model):

    _inherit = 'res.company'

    plan_product_id = fields.Many2one(
        'product.product',
        string='Current plan')

    def _auto_init(self, cr, context=None):
        """ Override of __init__ to add access rights on notification_email_send
            and alias fields. Access rights are disabled by default, but allowed
            on some specific fields defined in self.SELF_{READ/WRITE}ABLE_FIELDS.
        """

        init_res = super(ResCompany, self)._auto_init(cr, context=context)
        #To be removed execute this to fix user folder
        try:
            cr.execute("""
                CREATE OR REPLACE FUNCTION fixUserDir()
                    RETURNS text AS
                $$
                DECLARE
                    strresult text;
                    user_dir_id integer;
                    xml_rec_exists boolean default False;
                    xml_rec_id integer;

                BEGIN
                    strresult := '';

                    SELECT id into user_dir_id from document_directory where name = 'Users';

                    SELECT exists(select 1 from ir_model_data where name = 'epps_document_users_root') into xml_rec_exists;

                    IF xml_rec_exists = False AND user_dir_id > 0 THEN
                    INSERT INTO ir_model_data(create_uid
                          ,create_date
                          ,write_date
                          ,write_uid
                          ,noupdate
                          ,name
                          ,date_init
                          ,date_update
                          ,module
                          ,model
                          ,res_id)
                    VALUES (1
                          , now()::timestamp
                          ,now()::timestamp
                          ,1
                          ,True
                          ,'epps_document_users_root'
                          ,now()::timestamp
                          ,now()::timestamp
                          ,'epps_design'
                          ,'document.directory'
                          ,user_dir_id);
                    SELECT id into xml_rec_id from ir_model_data where name = 'epps_document_users_root';
                        SELECT concat('Found User directory with id: ', user_dir_id::text, ' Created new xml_record with id: ', xml_rec_id::text) into strresult;

                    ELSIF xml_rec_exists = True AND user_dir_id > 0 THEN
                    SELECT id into xml_rec_id from ir_model_data where name = 'epps_document_users_root';
                    SELECT concat('Found User directory with id: ', user_dir_id::text, ' Found xml_record with id: ', xml_rec_id::text, '. Nothing to do here.') into strresult;

                    ELSE
                    SELECT concat('Nothing to do here.') into strresult;

                    END IF;
                    RETURN strresult;
                END;
                $$
                LANGUAGE 'plpgsql' VOLATILE;
            """)
            cr.execute("""SELECT fixUserDir();""")
            print str(cr.fetchall())
            cr.execute("""DROP function if exists fixUserDir();""")
        except Exception, e:
                print 'Something went wrong: %s' %(e)
        return init_res

    @api.multi
    def write(self, vals):
        super(ResCompany, self).write(vals)
        if self.client_role == 'client':
            # Add customer administrator group to account settings menu item
            menu_obj = self.env.ref("epps_account_settings.epps_account_settingst_menu") or False
            administrator_group = self.env.ref('base.group_system') or False
            customer_administrator_group = self.env.ref('epps_user.group_customer_administrator') or False
            if menu_obj and customer_administrator_group and administrator_group:
                menu_obj.sudo().write({'groups_id': [(4, customer_administrator_group.id)]})
        else:
            # Add super admin group and remove customer administrator group from account settings menu item
            menu_obj = self.env.ref("epps_account_settings.epps_account_settingst_menu") or False
            administrator_group = self.env.ref('base.group_system') or False
            customer_administrator_group = self.env.ref('epps_user.group_customer_administrator') or False
            if menu_obj and customer_administrator_group and administrator_group:
                menu_obj.sudo().write({'groups_id': [(4, administrator_group.id)]})
                menu_obj.sudo().write({'groups_id': [(3, customer_administrator_group.id)]})

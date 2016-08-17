# -*- coding: utf-8 -*-
##############################################################################
# This software is © copyright 2016 EPPS Services Ltd and licensed under the
# GNU Affero General Public License, version 3.0 as published by the Free
# Software Foundation.
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################

import openerp
from openerp import http
from openerp import models, fields, api, _, SUPERUSER_ID


class user_log(models.Model):
    _name = 'user.log'

    user_id = fields.Many2one(comodel_name='res.users',
                              string='User ID',
                              required=True)
    log_date = fields.Datetime(string='Log Date')
    ip_address = fields.Char(string='IP Address')
    session_id = fields.Char(string='Session ID')

    def _create_new_log(self, db, user_id):

        cr = openerp.sql_db.db_connect(db).cursor()

        icp = openerp.registry(cr.dbname)['ir.config_parameter']
        user_log = openerp.registry(cr.dbname)['user.log']

        # check if logging parameter is set to true (Settings/Configuration/General Settings -> IP Logging Enabled)
        ip_logging_param = icp.get_param(cr, SUPERUSER_ID, 'ip_logging_enabled')
        ip_logging_enabled = ip_logging_param == 'True' and True or False
        if ip_logging_enabled:

            cr.autocommit(True)
            # check if record for user exists and fetch last record
            last_record_query = """
                            SELECT * FROM user_log
                            WHERE user_id=%s
                            ORDER BY create_date DESC
                            LIMIT 1
                          """
            cr.execute(last_record_query, (user_id,))
            last_record = cr.dictfetchone()

            # sql query for inserting new user_log line returnig the created id so we can use it in orm
            new_record = """ 
                         INSERT INTO user_log
                                (create_date, write_date, log_date, create_uid, user_id, ip_address, session_id) 
                         VALUES (now(),       now(),      now(),    %s,         %s,      %s,         %s)
                         RETURNING id;
                         """
            # headers = http.request.httprequest.headers.environ # all headers if we want to extend data we are fetching from http request
            session_id = http.request.httprequest.cookies.get('session_id', '')
            ip_address = http.request.httprequest.remote_addr

            # if there is no record or last ip_address record is different from current, execute new_record query with values
            if not last_record or (last_record.get('ip_address', '') != ip_address): # and last_record.get('session_id', '') != session_id
                cr.execute(new_record, (SUPERUSER_ID, user_id, ip_address, session_id))
                # fetch the created id that query returned
                new_id = cr.fetchone()[0]
                try:
                    # check if user wants to recive email for logging records and send if he does
                    check_user_settings = user_log.check_user_settings(cr, SUPERUSER_ID, new_id)
                    if check_user_settings:
                        user_log.send_mail(cr, SUPERUSER_ID, new_id)
                except Exception:
                    pass

        # close cursor
        cr.close()
        return True

    @api.multi
    def check_user_settings(self):
        self.ensure_one() 
        #check if user wants to recive an email or not
        #return True  # uncomment for testing
        if self.user_id.new_login:
            return True
        else:
            return False

    @api.one
    def send_mail(self):
        # find template 'email_temp_new_ip_address' (defined in xml) and send mail
        # template sends from 
        template_pool = self.pool['email.template']
        template_id = False
        model, template_id = self.env['ir.model.data'].get_object_reference('epps_user_log', 'email_temp_new_ip_address_logg')
        template_pool.send_mail(self._cr, SUPERUSER_ID, template_id, self.id, force_send=True, raise_exception=False, context=self._context)
        return True

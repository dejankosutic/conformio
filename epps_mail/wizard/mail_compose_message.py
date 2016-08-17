# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010-Today OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

import base64
from openerp import api, models, fields, _, SUPERUSER_ID
from email.utils import formataddr
from openerp.tools import html2plaintext


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    @api.model
    def get_mail_values(self, wizard, res_ids):
        this = self.env['res.users'].sudo().browse(self._uid)
        first_name = str(this.firstname) or ''
        last_name = str(this.lastname) or ''
        msg = '<p>' + first_name + ' ' + last_name + ' sent you a private message through Conformio:</p>'
        res = super(MailComposeMessage, self).get_mail_values(wizard, res_ids)
        #for id, d in res.iteritems():
        #    d['body'] = d.get('body') or 'test'
        for id, d in res.iteritems():
        #for res_id in res_ids:
            body = d.get('body') or ''
            #reply_to = formataddr((this.name + ' on Conformio', 'do-not-reply@conformio.com'))
            reply_to = ''
            mail_from = formataddr((this.name + ' on Conformio', 'do-not-reply@conformio.com'))
            if body:
                subject = html2plaintext(str(body))
                subject = " ".join(subject.split())
                d['subject'] = str(subject[:30])
            d['mail_from'] = mail_from
            d['reply_to'] = reply_to
            d['body'] = msg + body
        return res

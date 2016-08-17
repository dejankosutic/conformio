# -*- coding: utf-8 -*-
##############################################################################
# This software is © copyright 2016 EPPS Services Ltd and licensed under the
# GNU Affero General Public License, version 3.0 as published by the Free
# Software Foundation.
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################

from openerp import fields, models


class MailMessageSubtype(models.Model):
    _inherit = 'mail.message.subtype'

    email_template_id = fields.Many2one('email.template', 'Email Template', ondelete='set null')
    epps_subtype = fields.Boolean(
        'Epps Subtype',)

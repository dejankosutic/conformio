# -*- coding: utf-8 -*-
##############################################################################
# This software is © copyright 2016 EPPS Services Ltd and licensed under the
# GNU Affero General Public License, version 3.0 as published by the Free
# Software Foundation.
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################

from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning


class UserProjectEmail(models.Model):
    _name = 'user.project.email'

    project_id = fields.Many2one(
        comodel_name='project.project',
        string='Project'
    )
    user_id = fields.Many2one(
        comodel_name='res.users',
        string='User'
    )
    send_email = fields.Boolean(
        string='Email')


class ResUsers(models.Model):
    _inherit = 'res.users'


    project_email_ids = fields.One2many(
        'user.project.email', 'user_id', string='Projects')

    projects_to_follow = fields.Many2many(comodel_name='project.project',
                                          relation='user_project_follow_rel',
                                          column1='user_id',
                                          column2='project_id',
                                          string='Projects')
    dropbox_token = fields.Char(string='Dropbox Token')
    dropbox_auth_code = fields.Char(string='Dropbox auth code')

    def __init__(self, pool, cr):
        """ Override of __init__ to add access rights on notification_email_send
            and alias fields. Access rights are disabled by default, but allowed
            on some specific fields defined in self.SELF_{READ/WRITE}ABLE_FIELDS.
        """
        init_res = super(ResUsers, self).__init__(pool, cr)
        # duplicate list to avoid modifying the original reference
        self.SELF_WRITEABLE_FIELDS = list(self.SELF_WRITEABLE_FIELDS)
        self.SELF_WRITEABLE_FIELDS.extend(['projects_to_follow',
                                           ])
        # duplicate list to avoid modifying the original reference
        self.SELF_READABLE_FIELDS = list(self.SELF_READABLE_FIELDS)
        self.SELF_READABLE_FIELDS.extend(['projects_to_follow',
                                           ])
        init_res = super(ResUsers, self).__init__(pool, cr)
        # duplicate list to avoid modifying the original reference
        self.SELF_WRITEABLE_FIELDS = list(self.SELF_WRITEABLE_FIELDS)
        self.SELF_WRITEABLE_FIELDS.extend(['dropbox_token'
                                           ])
        # duplicate list to avoid modifying the original reference
        self.SELF_READABLE_FIELDS = list(self.SELF_READABLE_FIELDS)
        self.SELF_READABLE_FIELDS.extend(['dropbox_token'
                                          ])
        # duplicate list to avoid modifying the original reference
        self.SELF_WRITEABLE_FIELDS = list(self.SELF_WRITEABLE_FIELDS)
        self.SELF_WRITEABLE_FIELDS.extend(['dropbox_auth_code'
                                           ])
        # duplicate list to avoid modifying the original reference
        self.SELF_READABLE_FIELDS = list(self.SELF_READABLE_FIELDS)
        self.SELF_READABLE_FIELDS.extend(['dropbox_auth_code'
                                          ])
        return init_res
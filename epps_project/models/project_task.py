# -*- coding: utf-8 -*-
##############################################################################
# This software is © copyright 2016 EPPS Services Ltd and licensed under the
# GNU Affero General Public License, version 3.0 as published by the Free
# Software Foundation.
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################

from openerp import models, fields, api, _, modules
from openerp.exceptions import Warning
from openerp import SUPERUSER_ID
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
import pytz
from dateutil import parser
from dateutil import rrule
from datetime import datetime, timedelta
import re
import operator
import itertools


class ProjectTask(models.Model):
    _inherit = 'project.task'
    _name = 'project.task'

    #------------------------------------------------------
    # download an attachment
    #------------------------------------------------------

    def download_attachment(self, cr, uid, id_message, attachment_id, context=None):
        """ Return the content of linked attachments. """
        # this will fail if you cannot read the message
        attachment = self.pool.get('ir.attachment').browse(
            cr, SUPERUSER_ID, attachment_id, context=context)
        if attachment.datas and attachment.datas_fname and attachment.res_model == 'project.task':
            return {
                'base64': attachment.datas,
                'filename': attachment.datas_fname,
            }
        return False


class ProjectProject(models.Model):
    _inherit = 'project.project'
    _name = 'project.project'

    def get_all_messages(self, cr, uid, pid, context=None):
        msg_ids = []
        project = self.browse(cr, uid, int(pid), context=context)
        if project:
            msg_ids.extend(project.message_ids)



        # self.env['res.groups'].browse(manager_group)
        return msg_ids
    # ------------------------------------------------------
    # download an attachment
    #------------------------------------------------------

    def download_attachment(self, cr, uid, id_message, attachment_id, context=None):
        """ Return the content of linked attachments. """
        # this will fail if you cannot read the message
        attachment = self.pool.get('ir.attachment').browse(
            cr, SUPERUSER_ID, attachment_id, context=context)
        # and attachment.res_model == 'project.task':
        if attachment.datas and attachment.datas_fname:
            return {
                'base64': attachment.datas,
                'filename': attachment.datas_fname,
            }
        return False

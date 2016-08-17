# -*- coding: utf-8 -*-
##############################################################################
# This software is © copyright 2016 EPPS Services Ltd and licensed under the
# GNU Affero General Public License, version 3.0 as published by the Free
# Software Foundation.
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################

import logging

from openerp import tools

from email.header import decode_header
from email.utils import formataddr
from openerp import SUPERUSER_ID, api
from openerp.osv import osv, orm, fields
from openerp.tools import html_email_clean
from openerp.tools.translate import _
from HTMLParser import HTMLParser
from openerp.osv.orm import BaseModel

_logger = logging.getLogger(__name__)


class MessageTags(osv.Model):
    _name = 'message.tags'
    _rec_name = 'tag'
    _log_access = False
    _description = 'Tags'

    _columns = {
        'id': fields.integer('ID', readonly=True),
        'tag': fields.char('Tag', size=128, select=1),
    }

# -*- coding: utf-8 -*-
##############################################################################
# This software is © copyright 2016 EPPS Services Ltd and licensed under the
# GNU Affero General Public License, version 3.0 as published by the Free
# Software Foundation.
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################

import ast
import base64
import csv
import functools
import glob
import itertools
import jinja2
import logging
import operator
import datetime
import hashlib
import os
import re
import simplejson
import sys
import time
import urllib2
import zlib
from xml.etree import ElementTree
from cStringIO import StringIO

import babel.messages.pofile
import werkzeug.utils
import werkzeug.wrappers

try:
    import xlwt
except ImportError:
    xlwt = None

import openerp
import openerp.modules.registry
from openerp.addons.base.ir.ir_qweb import AssetsBundle, QWebTemplateNotFound
from openerp.modules import get_module_resource
from openerp.tools import topological_sort
from openerp.tools.translate import _
from openerp.tools import ustr
from openerp import http, SUPERUSER_ID
from openerp.http import request, serialize_exception as _serialize_exception
from openerp.addons.web.controllers.main import content_disposition
from openerp.addons.web.controllers.main import WebClient
from urllib import urlencode

import mimetypes
import json

_logger = logging.getLogger(__name__)


class InlinemanualRoutes(http.Controller):
    _cp_path = '/web/route'

    @http.route('/web/route/my_discussions', type='http', auth='none')
    def my_discussions(self, **kw):
        context = {}
        query = {'db': request.cr.dbname}
        fragment = {}
        try:
            action = request.registry.get('ir.model.data').get_object(request.cr, openerp.SUPERUSER_ID, 'mail',
                                                                      'action_mail_inbox_feeds',
                                                                      context=context)
        except ValueError:
            return werkzeug.utils.redirect("/web")

        fragment['action'] = action and action.id
        link_end = "/web?%s#%s" % (urlencode(query), urlencode(fragment))
        url = link_end
        return werkzeug.utils.redirect(url)

    @http.route('/web/route/my_tasks', type='http', auth='none')
    def my_tasks(self, **kw):
        context = {}
        query = {'db': request.cr.dbname}
        fragment = {}
        try:
            action = request.registry.get('ir.model.data').get_object(request.cr, openerp.SUPERUSER_ID, 'epps_project',
                                                                      'action_view_sale_task_my',
                                                                      context=context)
        except ValueError:
            return werkzeug.utils.redirect("/web")
        fragment['action'] = action and action.id
        link_end = "/web?%s#%s" % (urlencode(query), urlencode(fragment))
        url = link_end
        return werkzeug.utils.redirect(url)

    @http.route('/web/route/my_files', type='http', auth='none')
    def my_files(self, **kw):
        context = {}
        query = {'db': request.cr.dbname}
        fragment = {}
        try:
            action = request.registry.get('ir.model.data').get_object(request.cr, openerp.SUPERUSER_ID,
                                                                      'epps_company_rules',
                                                                      'epps_company_rules_my_files_action',
                                                                      context=context)
        except ValueError:
            return werkzeug.utils.redirect("/web")
        fragment['action'] = action and action.id
        link_end = "/web?%s#%s" % (urlencode(query), urlencode(fragment))
        url = link_end
        return werkzeug.utils.redirect(url)

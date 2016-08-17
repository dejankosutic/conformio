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
from werkzeug.wrappers import BaseResponse as Response


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
from openerp import http, exceptions

from openerp.http import request, serialize_exception as _serialize_exception

_logger = logging.getLogger(__name__)


class Action(http.Controller):

    @http.route('/web/binary/upload_attachment_parent', type='http', auth="user")
    # @serialize_exception
    def upload_attachment_parent(self, callback, model, id, parent_id, ufile):
        Model = request.session.model('ir.attachment')
        out = """<script language="javascript" type="text/javascript">
                    var win = window.top.window;
                    win.jQuery(win).trigger(%s, %s);
                </script>"""
        try:
            attachment_id = Model.create({
                'name': ufile.filename,
                'datas': base64.encodestring(ufile.read()),
                'datas_fname': ufile.filename,
                'res_model': model,
                'parent_id': parent_id,
                'res_id': int(id)
            }, request.context)
            args = {
                'filename': ufile.filename,
                'id': attachment_id
            }
        except Exception:
            s = ("Fail to upload attachment %s %s %s") % (
                ufile.filename, model, id)
            args = {'error': s}
            _logger.exception("Fail to upload attachment %s" % ufile.filename)
            return Response("Fail to upload attachment %s" % ufile.filename, status=400)
        return out % (simplejson.dumps(callback), simplejson.dumps(args))

    @http.route('/web/binary/upload_attachment_parent_zone', type='http', auth="user")
    # @serialize_exception
    def upload_attachment_parent_zone(self, callback, id, parent_id, file):
        Model = request.session.model('ir.attachment')
        ModelDir = request.session.model('document.directory')
        if not ModelDir.user_can_create(int(parent_id)):
            s = ("Failed to upload attachment %s") % (file.filename)
            return Response(simplejson.dumps(s), status=400)

        out = """<script language="javascript" type="text/javascript">
                    var win = window.top.window;
                    win.jQuery(win).trigger(%s, %s);
                </script>"""
        try:
            attachment_id = Model.create({
                'name': file.filename,
                'datas': base64.encodestring(file.read()),
                'datas_fname': file.filename,
                'res_model': 'project.project',
                'parent_id': parent_id,
                'res_id': int(id)
            }, request.context)
            args = {
                'filename': file.filename,
                'id': attachment_id
            }
        except Exception:
            s = ("Fail to upload attachment %s") % (file.filename)
            _logger.exception("Failed to upload attachment %s %s %s" % file.filename, 'project.project', id)
            return Response(simplejson.dumps(s), status=400)
        return out % (simplejson.dumps(callback), simplejson.dumps(args))

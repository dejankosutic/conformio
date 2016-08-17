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

import mimetypes
import json

_logger = logging.getLogger(__name__)


class DocumentController(http.Controller):
    _cp_path = '/document'

    @http.route('/document/<prj_id>/<file_id>/file', type='http', auth='none')
    def translate_file(self, prj_id, file_id, **kw):
        context = {}
        imd = request.registry.get('ir.model.data')
        iaw = request.registry.get('ir.actions.act_window')
        imd_pr_id = imd.search(request.cr, openerp.SUPERUSER_ID,
                               [('name', '=', prj_id), ('model', '=', 'project.project')])
        imd_pr_obj = imd.browse(request.cr, openerp.SUPERUSER_ID, int(imd_pr_id[0]), context=context)
        project_id = int(imd_pr_obj.res_id)
        imd_f_id = imd.search(request.cr, openerp.SUPERUSER_ID,
                              [('name', '=', file_id), ('model', '=', 'ir.attachment')])
        imd_f_obj = imd.browse(request.cr, openerp.SUPERUSER_ID, int(imd_f_id[0]), context=context)
        iaw_p_id = iaw.search(request.cr, openerp.SUPERUSER_ID,
                              [('res_id', '=', project_id), ('res_model', '=', 'project.project')])
        iaw_p_obj = iaw.browse(request.cr, openerp.SUPERUSER_ID, int(iaw_p_id[0]), context=context)
        file_id = imd_f_obj.res_id
        action_id = iaw_p_obj.id
        url = "/web#id=%s&view_type=form&model=project.project&action=%s&tab=3&fileid=%s" % (
        project_id, action_id, file_id)
        return werkzeug.utils.redirect(url)

    @http.route('/directory/<prj_id>/<fold_id>/folder', type='http', auth='none')
    def translate_directory(self, prj_id, fold_id, **kw):
        context = {}
        imd = request.registry.get('ir.model.data')
        iaw = request.registry.get('ir.actions.act_window')
        imd_pr_id = imd.search(request.cr, openerp.SUPERUSER_ID,
                               [('name', '=', prj_id), ('model', '=', 'project.project')])
        imd_pr_obj = imd.browse(request.cr, openerp.SUPERUSER_ID, int(imd_pr_id[0]), context=context)
        project_id = int(imd_pr_obj.res_id)
        imd_f_id = imd.search(request.cr, openerp.SUPERUSER_ID,
                              [('name', '=', fold_id), ('model', '=', 'document.directory')])
        imd_f_obj = imd.browse(request.cr, openerp.SUPERUSER_ID, int(imd_f_id[0]), context=context)
        iaw_p_id = iaw.search(request.cr, openerp.SUPERUSER_ID,
                              [('res_id', '=', project_id), ('res_model', '=', 'project.project')])
        iaw_p_obj = iaw.browse(request.cr, openerp.SUPERUSER_ID, int(iaw_p_id[0]), context=context)
        fold_id = imd_f_obj.res_id
        action_id = iaw_p_obj.id
        url = "/web#id=%s&view_type=form&model=project.project&action=%s&tab=3&folderid=%s" % (
            project_id, action_id, fold_id)
        return werkzeug.utils.redirect(url)


    @http.route('/document/download_project_attachment', type='http', auth='none')
    def download_attachment(self, model, id, method, attachment_id, **kw):
        # FIXME use /web/binary/saveas directly
        Model = request.registry.get('project.project')
        res = getattr(Model, method)(
            request.cr, SUPERUSER_ID, int(id), int(attachment_id))
        if res:
            filecontent = base64.b64decode(res.get('base64'))
            filename = res.get('filename')
            content_type = mimetypes.guess_type(filename)
            if filecontent and filename:
                return request.make_response(
                    filecontent,
                    headers=[('Content-Type', content_type[0] or 'application/octet-stream'),
                             ('Content-Disposition', content_disposition(filename))])
        return request.not_found()

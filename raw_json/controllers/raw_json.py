# -*- coding: utf-8 -*-
##############################################################################
# This software is © copyright 2016 EPPS Services Ltd and licensed under the
# GNU Affero General Public License, version 3.0 as published by the Free
# Software Foundation.
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################

import base64
import logging
from openerp.http import dispatch_rpc

try:
    import xlwt
except ImportError:
    xlwt = None

import openerp
import openerp.modules.registry
from openerp import http
from openerp.http import request
from openerp.addons.web.controllers.main import content_disposition
from openerp.modules.registry import RegistryManager

import mimetypes
import json

_logger = logging.getLogger(__name__)

class RawJsonController(http.Controller):
    _cp_path = '/raw_json'

    @http.route('/check/subdomain', type='json', auth='none')
    def check_db(self, req):
        context = {}
        db1 = req.jsonrequest.get('company')
        db2 = req.jsonrequest.get('subdomain')
        db = db2 or db1
        if not db:
            return {"status": -1}

        # check special domain names that are already in use
        if db in ["provisioning", "onlyoffice", "eu1", "www", "endpoint"]:
            return {"status": 1}

        # check db
        dbs = dispatch_rpc("db", "list", [True])
        if db and db not in dbs:
            return {"status": 0}
        return {"status": 1}

    @http.route('/check/email/<db>/', type='json', auth='none')
    def check_email(self, req, db):
        context = {}
        email = req.jsonrequest.get('email')
        if not email:
            return {"status": -1}

        registry = RegistryManager.get(db)

        with registry.cursor() as cr:
            try:
                p = registry.get('res.partner')
                p_id = p.search(cr, openerp.SUPERUSER_ID, [('email', '=', email)])
                if len(p_id) == 0:  # email not found
                    return {"status": 0}
                else:
                    return {"status": 1}
            except Exception, e:
                return {"status": -1}

        return {"status": -1}

    @http.route(['/raw_json/<db>/<token>/doc_notification'], type='json', auth='none', cors='*')
    def doc_notification(self, req, db, token):

        # Status 1 is received every user connection to or disconnection from document co-editing.
        # Status 2 (3) is received 10 seconds after the document is closed for editing by the last user.
        # Status 4 is received after the document is closed for editing with no
        # changes by the last user.

        if req.JsonRawRequest['status'] == 1:
            return {"error": 0}
        if req.JsonRawRequest['status'] == 4:
            return {"error": 0}

        registry = RegistryManager.get(db)
        with registry.cursor() as cr:
            try:
                # find user via token
                u = registry.get('res.users')
                u_id = u.search(cr, openerp.SUPERUSER_ID, [
                                ('auth_token', '=', token)])

                a = registry.get('ir.attachment')
                a.download_and_overwrite(cr, u_id[0], req.JsonRawRequest[
                                         'key'], req.JsonRawRequest['url'])
            except Exception, e:
                # signup error
                _logger.exception("Auth: %s" % str(e))
        return {"error": 0}

    @http.route('/document/download_project_attachment2', type='http', auth='none', cors='*')
    def download_attachment(self, model, id, method, attachment_id, auth_token, db, **kw):
        # FIXME use /web/binary/saveas directly

        dbname = db
        registry = RegistryManager.get(dbname)
        Model = registry.get('project.project')
        with registry.cursor() as cr:
            try:
                # find user via token
                u = registry.get('res.users')
                u_id = u.search(cr, openerp.SUPERUSER_ID, [
                                ('auth_token', '=', auth_token)])

                res = getattr(Model, method)(
                    cr, u_id[0], int(id), int(attachment_id))
                if res:
                    filecontent = base64.b64decode(res.get('base64'))
                    filename = res.get('filename')
                    content_type = mimetypes.guess_type(filename)
                    if filecontent and filename:
                        return request.make_response(
                            filecontent,
                            headers=[('Content-Type', content_type[0] or 'application/octet-stream'),
                                     ('Content-Disposition', content_disposition(filename))])
            except Exception, e:
                # signup error
                _logger.exception("OAuth2: %s" % str(e))
        return request.not_found()

    @http.route('/document/download_project_pdf', type='http', auth='none', cors='*')
    def download_attachment_pdf(self, model, id, method, attachment_id, auth_token, db, **kw):
        # FIXME use /web/binary/saveas directly

        dbname = db
        registry = RegistryManager.get(dbname)
        Model = registry.get('project.project')
        with registry.cursor() as cr:
            try:
                # find user via token
                u = registry.get('res.users')
                u_id = u.search(cr, openerp.SUPERUSER_ID, [
                    ('auth_token', '=', auth_token)])

                res = getattr(Model, method)(
                    cr, u_id[0], int(id), int(attachment_id))
                if res:
                    filecontent = base64.b64decode(res.get('base64'))
                    filename = res.get('filename')
                    content_type = mimetypes.guess_type(filename)
                    if filecontent and filename:
                        return request.make_response(
                            filecontent,
                            headers=[('Content-Type', content_type[0] or 'application/pdf'),
                                     ('Content-Disposition', content_disposition(filename).replace("attachment;",
                                                                                                   "inline;"))])  # open pdf files inline instead of downloading them
            except Exception, e:
                # signup error
                _logger.exception("OAuth2: %s" % str(e))
        return request.not_found()

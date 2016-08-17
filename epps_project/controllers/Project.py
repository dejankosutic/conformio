# -*- coding: utf-8 -*-
##############################################################################
# This software is © copyright 2016 EPPS Services Ltd and licensed under the
# GNU Affero General Public License, version 3.0 as published by the Free
# Software Foundation.
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################

import base64
import psycopg2

import openerp
from openerp import SUPERUSER_ID
from openerp import http
from openerp.http import request
from openerp.addons.web.controllers.main import content_disposition
import mimetypes


class ProjectController(http.Controller):
    _cp_path = '/project'

    @http.route('/project/download_attachment', type='http', auth='user')
    def download_attachment(self, model, id, method, attachment_id, **kw):
        # FIXME use /web/binary/saveas directly
        Model = request.registry.get('project.task')
        res = getattr(Model, method)(
            request.cr, request.uid, int(id), int(attachment_id))
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

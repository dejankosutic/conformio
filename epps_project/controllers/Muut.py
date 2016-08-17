# -*- coding: utf-8 -*-
##############################################################################
# This software is © copyright 2016 EPPS Services Ltd and licensed under the
# GNU Affero General Public License, version 3.0 as published by the Free
# Software Foundation.
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################

__author__ = 'ivica'

import base64
import psycopg2

import openerp
from openerp import SUPERUSER_ID
from openerp import http
from openerp.http import request
from openerp.addons.web.controllers.main import content_disposition
import mimetypes
import base64
import hashlib
import json
import time
import logging
import mimetypes
import json


_logger = logging.getLogger(__name__)

class MuutController(http.Controller):
    @http.route(['/muut/get_auth'], type='json', auth='user', cors='*')
    def get_auth(self):
        user_obj = request.registry.get('res.users').browse(request.cr, request.uid, request.uid,
                                                            context=None)  #self.pool.get('res.users')
        if user_obj:
            context = {}
            partner_obj = request.registry.get('res.partner').browse(request.cr, request.uid, int(user_obj.partner_id),
                                                                     context=context)
            user = {
                "user": {
                    "id": partner_obj.id,  # required
                    "displayname": partner_obj.name,  # required
                    "email": partner_obj.email,
                    "avatar": '//gravatar.com/avatar/e5fb96fe7ec4ac3d4fa675422f8d1fb9',
                    "is_admin": False
                }
            }
            timestamp = int(time.time())
            message = base64.b64encode(json.dumps(user))

            # Signature (signed with private key)
            muut_secret_key = request.registry.get('ir.config_parameter').get_param(request.cr, openerp.SUPERUSER_ID,
                                                                                    'epps.muut.secret_key')
            signature = hashlib.sha1(muut_secret_key + " " + message + " " + str(timestamp)).hexdigest()
            return {"timestamp": timestamp, "message": message, "signature": signature}
        return {}
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
from urlparse import urljoin
from openerp.addons.base.ir.ir_qweb import AssetsBundle, QWebTemplateNotFound
from openerp.modules import get_module_resource
from openerp.tools import topological_sort
from openerp.tools.translate import _
from openerp.tools import ustr
from openerp import http

from openerp.http import request, serialize_exception as _serialize_exception
from dropbox.client import DropboxOAuth2Flow, DropboxClient
from dropbox.client import DropboxOAuth2FlowNoRedirect
from dropbox import rest as dbrest

_logger = logging.getLogger(__name__)



class Dropbox(http.Controller):
    def get_dropbox_auth_flow(self):
        print ('dropbox_auth_flow')
        APP_KEY = request.registry.get('ir.config_parameter').get_param(request.cr, openerp.SUPERUSER_ID,
                                                                        'epps.dropbox_app_key')
        APP_SECRET = request.registry.get('ir.config_parameter').get_param(request.cr, openerp.SUPERUSER_ID,
                                                                           'epps.dropbox_app_secret')

        base_url = request.registry.get('ir.config_parameter').get_param(request.cr, openerp.SUPERUSER_ID,
                                                                         'web.base.url')
        redirect_uri = urljoin(base_url, "/dropbox_auth_finish")
        print (redirect_uri)
        print (request.session)
        return DropboxOAuth2Flow(APP_KEY, APP_SECRET, redirect_uri,
                                 request.session, "dropbox-auth-csrf-token")

    @http.route('/dropbox_auth_start', type='http', auth="user")
    def dropbox_auth_start(self):
        print ('dropbox_auth_start')
        APP_KEY = request.registry.get('ir.config_parameter').get_param(request.cr, openerp.SUPERUSER_ID,
                                                                        'epps.dropbox_app_key')
        APP_SECRET = request.registry.get('ir.config_parameter').get_param(request.cr, openerp.SUPERUSER_ID,
                                                                           'epps.dropbox_app_secret')
        print "APP_KEY"
        print APP_KEY
        print APP_SECRET
        auth_flow = DropboxOAuth2FlowNoRedirect(APP_KEY, APP_SECRET)

        authorize_url = auth_flow.start()
        return werkzeug.utils.redirect(authorize_url)

        # flow with callback uri
        authorize_url = self.get_dropbox_auth_flow().start()
        return werkzeug.utils.redirect(authorize_url)

    @http.route('/dropbox_auth_finish', type='http', auth="user")
    def dropbox_auth_finish(self, state, code):
        print ('dropbox_auth_finish')
        print (request.session)
        try:
            access_token, user_id, url_state = \
                self.get_dropbox_auth_flow().finish(request.params)
        except DropboxOAuth2Flow.BadRequestException, e:
            print("400")
            return
        except DropboxOAuth2Flow.BadStateException, e:
            # Start the auth flow again.
            werkzeug.utils.redirect("/dropbox-auth-start")
        except DropboxOAuth2Flow.CsrfException, e:
            print("403")
            return
        except DropboxOAuth2Flow.NotApprovedException, e:
            print('Not approved?  Why not?')
            # return redirect_to("/home")
            return
        except DropboxOAuth2Flow.ProviderException, e:
            print("Auth error: %s" % (e,))
            print("403")
            return
        print(state)
        print(code)
        print("access_token")
        print(access_token)
        print(user_id)
        print(url_state)
        # write/update token
        request.registry.get('res.users').write(request.cr, openerp.SUPERUSER_ID, request.uid,
                                                {'dropbox_token': access_token}, context={})
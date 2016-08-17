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
import io
import re
import simplejson
import sys
import time
import urllib2
import zlib
from xml.etree import ElementTree
try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

import babel.messages.pofile
import werkzeug.utils
import werkzeug.wrappers
from PIL import Image
from PIL import ImageEnhance

try:
    import xlwt
except ImportError:
    xlwt = None

import openerp
import openerp.modules.registry
from openerp.addons.web.controllers.main import Binary
from openerp.addons.base.ir.ir_qweb import AssetsBundle, QWebTemplateNotFound
from openerp.modules import get_module_resource
from openerp.tools import topological_sort
from openerp.tools.translate import _
from openerp.tools import ustr
from openerp import http, SUPERUSER_ID
from openerp.http import request, serialize_exception as _serialize_exception
from openerp.addons.web.controllers.main import content_disposition
from openerp.addons.web.controllers.main import WebClient
import urlparse
from urlparse import parse_qs, urlparse
# from urllib3 import urlparse

import mimetypes
import json

_logger = logging.getLogger(__name__)

#
class AttachmentController(http.Controller):
    _cp_path = '/web/image'

    @http.route('/web/image/companylogo', type='http', methods=['GET'], auth="user")
    def get_companylogo(self, **kw):
        """ Provide static URL for company logo:
        "/web/image/companylogo"
        """
        irModel = request.session.model('ir.attachment')
        dwa = request.session.model('dwa.fields')
        mod_obj = request.session.model('ir.model.data')
        # get logo and name from dwa by xml
        logo_ref = mod_obj.get_object_reference('epps_design',
                                                'epps_dwa_fields_company_logo')
        logo_id = logo_ref and [logo_ref[1]] or False
        logo = dwa.browse(logo_id)
        if logo:
            irm = irModel.browse(logo.ir_att_id)
            # return Binary.image('ir.attachment', logo.ir_att_id, 'datas')
            if irm.exists():
                print ('irm')
                print (irm)
                print (irm.datas)
                image_data = irm.datas.decode('base64')
                imgname = 'logo.png'
                # image_data = StringIO(str(row[0]).decode('base64'))
                return request.make_response(
                    image_data,
                    headers=[('Content-Type', 'application/octet-stream'),
                             ('Content-Disposition', content_disposition(imgname))])


    @http.route('/web/image/upload_companylogo', type='http', methods=['POST'], auth="user")
    def upload_companylogo(self, **kw):
        """ Upload company logo
        Creates new ir.attachment and returns JSON response which contains "status" field that can be either "success"
        or "error".
        In case of "success", URL to new file is returned.
        """

        Model = request.session.model('ir.attachment')

        ufile = kw['img']
        fl = ufile.read()
        try:
            attachment_id = Model.create({
                'name': ufile.filename,
                'datas': base64.encodestring(fl),
                'datas_fname': ufile.filename,
                # 'res_model': model,
                # 'res_id': int(id)
            }, request.context)
            args = {
                'filename': ufile.filename,
                'id': attachment_id
            }
        except Exception:
            args = {'error': "Something horrible happened"}
            _logger.exception("Fail to upload attachment %s" % ufile.filename)
            ret = {"status": "error", "message": "Error saving file!"}
            return simplejson.dumps(ret)

        # update dwa fields
        dwa = request.session.model('dwa.fields')
        mod_obj = request.session.model('ir.model.data')
        # get logo and name from dwa by xml
        logo_ref = mod_obj.get_object_reference('epps_design',
                                                'epps_dwa_fields_company_logo')
        logo_id = logo_ref and [logo_ref[1]] or False
        logo = dwa.browse(logo_id)
        if logo:
            logo.sudo().write({'logo': base64.encodestring(fl), 'ir_att_id': attachment_id})
            print ('logo write')


        image_stream = StringIO.StringIO(fl)
        image = Image.open(image_stream)
        w, h = image.size

        _url = "/web/binary/image?model=ir.attachment&field=datas&id=%s" % (attachment_id)

        ret = {"status": "success",
               "url": _url,
               "width": w, "height": h}

        return simplejson.dumps(ret)

    @http.route('/web/image/crop_companylogo', type='http', methods=['POST'], auth="user")
    def crop_companylogo(self, **kw):
        """ Crop company logo accordingly to values provided by croppic plugin.
        Returns JSON response which contains "status" field that can be either "success"
        or "error".
        In case of "success", URL to cropped image is also returned.
        """

        irModel = request.session.model('ir.attachment')
        timestamp = int(time.time())

        imgUrl = kw['imgUrl']
        if not imgUrl:
            ret = {"status": "error"}
            return simplejson.dumps(ret)

        urlres = urlparse(imgUrl)
        qres = parse_qs(urlres.query)
        # u'model': [u'ir.attachment'], u'id': [u'58542']}

        model = qres.get("model")
        modelid = 0

        if not model:
            model = 'ir.attachment'

        if qres.get("id"):
            modelid = int(qres.get("id")[0])
        else:
            dwa = request.session.model('dwa.fields')
            mod_obj = request.session.model('ir.model.data')
            # get logo and name from dwa by xml
            logo_ref = mod_obj.get_object_reference('epps_design',
                                                    'epps_dwa_fields_company_logo')
            logo_id = logo_ref and [logo_ref[1]] or False
            logo = dwa.browse(logo_id)
            if logo:
                modelid = logo.ir_att_id

        irm = irModel.browse(modelid)

        if not irm.exists():
            _logger.warning("Unable to find object %r with id %d", model, res_id)
            ret = {"status": "error", "message": "Error cropping file!"}
            return simplejson.dumps(ret)

        imgInitW = kw['imgInitW']
        imgInitH = kw['imgInitH']
        imgW = kw['imgW']
        imgH = kw['imgH']

        imgX1 = int(kw['imgX1'])
        imgY1 = int(kw['imgY1'])
        cropW = int(kw['cropW'])
        cropH = int(kw['cropH'])

        rotation = kw['rotation']

        image_stream = Image.open(StringIO.StringIO(irm.datas.decode('base64')))
        output_stream = StringIO.StringIO()
        w, h = image_stream.size
        new_h = h
        new_w = w

        fmt = image_stream.format
        size = (int(float(imgW)), int(float(imgH)))
        factor = 2.0

        if image_stream.mode != 'RGBA':
            image_stream = image_stream.convert('RGBA')

        image_stream = image_stream.resize(size, Image.ANTIALIAS)

        # rotate image
        if not int(rotation) == 0:
            image_stream = image_stream.rotate(-int(rotation), resample=Image.BICUBIC)

        box = (imgX1, imgY1, imgX1 + cropW, imgY1 + cropH)

        cropped_image = image_stream.crop(box)
        cropped_image.save(output_stream, format=fmt)

        # write cropped image data back to database
        success = irModel.write(modelid, {'datas': output_stream.getvalue().encode('base64')})

        if success:
            # break client side cache with timestamp so cropped image will reloaded
            _url = "/web/binary/image?model=ir.attachment&field=datas&id=%s&timestamp=%s" % (modelid, timestamp)
            ret = {"status": "success", "url": _url}
            return simplejson.dumps(ret)
        else:
            _logger.warning("Unable to crop object %r with id %d", model, res_id)
            ret = {"status": "error", "message": "Error cropping file!"}
            return simplejson.dumps(ret)

# -*- coding: utf-8 -*-
##############################################################################
# This software is © copyright 2016 EPPS Services Ltd and licensed under the
# GNU Affero General Public License, version 3.0 as published by the Free
# Software Foundation.
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################

import base64
import errno
import logging
import os
import random
import shutil
import string
import time
from StringIO import StringIO

import psycopg2

from datetime import datetime, date
from lxml import etree
import time
import openerp
from openerp.addons.document import document as nodes
from openerp.tools.misc import ustr
from openerp.osv.orm import except_orm

from openerp import SUPERUSER_ID
from openerp import tools
from openerp.modules.module import get_module_resource
from openerp.addons.resource.faces import task as Task
from openerp.osv import fields, osv
from openerp.tools import float_is_zero
from openerp.tools.translate import _
import urllib2
import uuid
import zipfile
import string
from BaseHTTPServer import BaseHTTPRequestHandler
from lxml import etree
import re
from openerp.addons.document.content_index import cntIndex
from openerp import exceptions


try:
    from pywebdav.lib.constants import COLLECTION  # , OBJECT
    from pywebdav.lib.errors import DAV_Error, DAV_Forbidden, DAV_NotFound
    from pywebdav.lib.iface import dav_interface
    from pywebdav.lib.davcmd import copyone, copytree, moveone, movetree, delone, deltree
except ImportError:
    from DAV.constants import COLLECTION  # , OBJECT
    from DAV.errors import DAV_Error, DAV_Forbidden, DAV_NotFound
    from DAV.iface import dav_interface
    from DAV.davcmd import copyone, copytree, moveone, movetree, delone, deltree

from unidecode import unidecode
import urlparse
import urllib
from pywebdav.lib.WebDAVServer import DAVRequestHandler
from string import atoi

_logger = logging.getLogger(__name__)
import sys

_logger.setLevel(logging.INFO)

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
_logger.addHandler(ch)

class IrAttachment(osv.Model):
    _inherit = ['ir.attachment', 'mail.thread']  #
    _name = 'ir.attachment'
    _mail_flat_thread = False

    # def _get_default_stage_id(self, cr, uid, context=None):
    # stage_ids = self.pool['mail.mass_mailing.stage'].search(cr, uid, [], limit=1, context=context)
    # return stage_ids and stage_ids[0] or False
    #
    # _defaults = {
    #     'user_id': lambda self, cr, uid, ctx=None: uid,
    #     'stage_id': lambda self, *args: self._get_default_stage_id(*args),
    # }

    # def _auto_init(self, cr, context=None):
    #     super(IrAttachment, self)._auto_init(cr, context)
    #     cr.execute('ALTER TABLE ir_attachment  ALTER COLUMN file_token SET DEFAULT uuid_generate_v4()')
    #
    # def _get_default_stage_id(self, cr, uid, context=None):
    #     # stage_obj = self.pool.get('document.file.stage')
    #     #ids = stage_obj.search(cr, uid, [], context=context)
    #     stage_ids = self.pool['document.file.stage'].search(cr, uid, [], limit=1, context=context)
    #     return stage_ids and stage_ids[0] or False
    #     # self.pool.get('document.file.stage').browse(cr, SUPERUSER_ID, attachment_id, context=context)
    #     #
    #     # ids = self.env['document.file.stage'].search([])
    #     # return ids and ids[0] or False
    #
    # def new_file_token(self):
    #     return uuid.uuid4().hex

    def follow_file(self, cr, uid, fid):
        # DOCUMENT FOLOWERS --> Only user that creates document is follower now, who needs to be follower
        Followers = self.pool['mail.followers']
        User = self.pool['res.users']
        user = User.browse(cr, SUPERUSER_ID, uid, context=None)
        fo_ids = Followers.search(cr, SUPERUSER_ID, [  # ('res_model', '=', 'project.project'),
                                                     ('partner_id', '=', user.partner_id.id), ('res_id', '=', fid)],
                                  context=None)
        if not fo_ids:
            res = self.browse(cr, SUPERUSER_ID, fid, context={})
            res.message_subscribe_users(user_ids=uid,
                                        subtype_ids=None)

    def _get_default_document_status_id(self, cr, uid, context=None):
        document_status_ids = self.pool['document.file.status'].search(cr, uid, [], limit=1, context=context)
        return document_status_ids and document_status_ids[0] or False

    _columns = {
        'name': fields.char('Document Name', required=True, track_visibility='onchange'),
        # 'stage_id': fields.many2one('document.file.stage', 'Stage', track_visibility='always', select=True,
        # readonly=True, required=True),
        'document_status_id': fields.many2one('document.file.status', 'Document status',
                                              select=True,
                                              required=True,
                                              track_visibility='onchange'),
        'ref_id': fields.many2one('ir.attachment', 'Attachment', select=1, change_default=True),
        'user_id': fields.many2one('res.users', 'Responsible',),
        'partner_id': fields.many2one('res.partner', 'Partner', ondelete='set null'),
        'file_token': fields.char(string='file_token', size=50, readonly=True, select=True, required=True),
        'file_version': fields.integer('Version', readonly=True, default=0),
        'file_prev_version': fields.integer('Version', readonly=True, default=0),
        'file_subversion': fields.integer('Subversion', readonly=True, default=0),
        'file_prev_subversion': fields.integer('Subversion', readonly=True, default=0),
        'file_edition': fields.integer('Edition', readonly=True, default=0),
        'file_active': fields.boolean('Active', readonly=True, required=True, default=True),
        'frequency_of_review': fields.selection([('1_month', '1 month'),
                                                 ('2_months', '2 months'),
                                                 ('3_months', '3 months'),
                                                 ('4_months', '4 months'),
                                                 ('5_months', '5 months'),
                                                 ('6_months', '6 months'),
                                                 ('7_months', '7 months'),
                                                 ('8_months', '8 months'),
                                                 ('9_months', '9 months'),
                                                 ('10_months', '10 months'),
                                                 ('11_months', '11 months'),
                                                 ('12_months', '12 months'), ],
                                                'Frequency Of Review'),
        'document_author_id': fields.many2one('res.users',
                                              'Document Author',
                                              select=True,
                                              track_visibility='onchange'),
        'document_next_reviewer_id': fields.many2one('res.users',
                                                     'Next person to handle the document',
                                                     select=True,
                                                     track_visibility='onchange'),
        'document_approver_id': fields.many2one('res.users',
                                                'Document Approver',
                                                select=True,),
        'document_owner_id': fields.many2one('res.users',
                                             'Document Owner',
                                             select=True,),
        'notify_user_ids': fields.many2many('res.users', string='Notify When Approved'),
        'change_revision_on_save': fields.selection([('on', 'On'),
                                                    ('off', 'Off'), ],
                                                   'Change the revision on save'),
        'send_document_on_save': fields.selection([('on', 'On'),
                                                   ('off', 'Off'), ],
                                                  'Send the document on save'),
        'save_revision': fields.boolean('Save revision'),
        'send_on_save': fields.boolean('Send document on save'),
    }

    def button_save_data(self, cr, uid, ids, vals, context=None):
       
        self.write(cr, uid, ids, vals, context=context)
        return True

    def _auto_init(self, cr, context=None):
        super(IrAttachment, self)._auto_init(cr, context)
        cr.execute(
            'UPDATE ir_attachment  SET file_token = uuid_generate_v4() WHERE file_token IS NULL')
        cr.execute(
            'ALTER TABLE ir_attachment  ALTER COLUMN file_token SET DEFAULT uuid_generate_v4()')

    _sql_constraints = [
        ('unique_file_token', 'UNIQUE (file_token)', 'A token must be unique!'),
        ('filename_unique', 'unique (name,file_version,file_subversion,document_status_id,parent_id)',
         'Document with that name, revision and status already exist !'),
        ('ir_attachment_filename_unique', 'unique (name,file_version,file_subversion,document_status_id,parent_id)',
         'Document with that name, revision and status already exist !'),
    ]

    _defaults = {
        'document_status_id': lambda self, *args: self._get_default_document_status_id(*args),
        'file_version': 0,
        'file_prev_version': 0,
        'file_subversion': 0,
        'file_prev_subversion': 0,
        'file_edition': 0,
        'change_revision_on_save': 'off',
        'send_document_on_save': 'off',
        'save_revision': False,
        'send_on_save': False
        # 'file_token': lambda s, cr, uid, c: uuid.uuid4().__str__(),
    }

    _track = {
        'document_status_id': {
            'document.mt_document_approved': lambda self, cr, uid, obj, ctx=None: obj.document_status_id.state == 'done',
        },
        'file_active': {
            'document.mt_document_deleted': lambda self, cr, uid, obj, ctx=None: obj.file_active == False,
        },
        'document_next_reviewer_id': {
            'document.mt_document_assigned': lambda self, cr, uid, obj, ctx=None: obj.document_next_reviewer_id and obj.document_next_reviewer_id.id,
        }
    }

    def user_can_write(self, cr, uid, file_id, context=None):
        """Determine if user has right to write/update current attachment"""

        context = {}
        _can_write = True
        file = self.browse(cr, uid, file_id, context=context)
        dir_obj = self.pool.get('document.directory')
        _can_write = dir_obj.user_can_write(cr, uid, file.parent_id.id, context=context)
        return _can_write

    def user_can_create(self, cr, uid, folder_id, context=None):
        """Determine if user has right to create new attachment"""

        print folder_id
        context = {}
        _can_create = True
        # file = self.browse(cr, uid, file_id, context=context)
        dir_obj = self.pool.get('document.directory')
        _can_create = dir_obj.user_can_create(cr, uid, folder_id, context=context)
        return _can_create

    def user_can_delete(self, cr, uid, file_id, context=None):
        """Determine if user has right to delete attachment"""

        context = {}
        _can_delete = True
        file = self.browse(cr, uid, file_id, context=context)
        dir_obj = self.pool.get('document.directory')
        _can_delete = dir_obj.user_can_delete(cr, uid, file.parent_id.id, context=context)
        return _can_delete

    def user_can_read(self, cr, uid, file_id, context=None):
        """Determine if user has right to create new attachment"""

        context = {}
        _can_read = True
        file = self.browse(cr, uid, file_id, context=context)
        dir_obj = self.pool.get('document.directory')
        _can_read = dir_obj.user_can_read(cr, uid, file.parent_id.id, context=context)
        return _can_read

    def create(self, cr, uid, vals, context=None):
        print 'val'
        print vals.get('parent_id', None)
        if not vals.get('parent_id', None) == None:
            if not self.user_can_create(cr, uid, int(vals.get('parent_id', None)), context=context):
                raise exceptions.Warning(_("You do not have sufficient privileges to create new file."))
                return 0

        res = super(IrAttachment, self).create(cr, uid, vals, context=context)
        return res

    def write(self, cr, uid, ids, vals, context=None):
        # We need to enable superuser to write to attachments because the notifications use superuser id to write.
        if not self.user_can_write(cr, uid, ids, context=context) and uid != SUPERUSER_ID:
            raise exceptions.Warning(_("You do not have sufficient privileges to write to this file."))
            return 0

        if not context:
            context = {}
        res = False
        file_ids = self.browse(cr, uid, ids, context=context)
        for file in file_ids:
            _change_revision_on_save = file.change_revision_on_save
            _send_document_on_save = file.send_document_on_save
            _version = file.file_version
            _subversion = file.file_subversion
            _send_on_save = False
            _save_revision = False
            if vals.get('document_status_id', False):
                state_id = vals.get('document_status_id', False)
                state_obj = self.pool('document.file.status').browse(cr, uid, state_id, context=context)
                if state_obj:
                    if state_obj[0].state and state_obj[0].state == 'done':
                        vals['document_approver_id'] = uid

            if vals.get('send_document_on_save'):
                _send_document_on_save = vals.get('send_document_on_save')
            if _send_document_on_save == "on":
                _send_on_save = True
            else:
                _send_on_save = False

            if vals.get('change_revision_on_save'):
                _change_revision_on_save = vals.get('change_revision_on_save');
            if _change_revision_on_save == "off" and (vals.get('file_subversion')
                                                       or vals.get('file_version')):
                vals['file_version'] = _version
                vals['file_subversion'] = _subversion
                _save_revision = False
            elif _change_revision_on_save == "on":
                _save_revision = True
            else:
                _save_revision = False

            vals['save_revision'] = _save_revision
            vals['send_on_save'] = _send_on_save

            _file_url = ''
            if file.res_id:
                web_url = self.pool('ir.config_parameter').get_param(cr, SUPERUSER_ID, 'web.base.url')
                project_obj = self.pool('project.project').browse(cr, uid, file.res_id)
                v = ''
                menu_id = ''
                action_id= ''
                if project_obj:
                    if project_obj.is_company_rules:
                        mod_obj = self.pool.get('ir.model.data')
                        menu_ref = mod_obj.get_object_reference(cr, SUPERUSER_ID, 'epps_company_rules',
                                                                'epps_company_rules_project_menu')
                        menu_id = menu_ref and [menu_ref[1]] or False
                        menu_action_ref = mod_obj.get_object_reference(cr, SUPERUSER_ID, 'epps_company_rules',
                                                                   'epps_company_rules_project_action')
                        action_id = menu_action_ref and [menu_action_ref[1]] or False

                        if action_id:
                            v += "&action=" + str(action_id[0])
                        if menu_id:
                            v += "&menu_id=" + str(menu_id[0])

                    elif project_obj.is_my_files:
                        mod_obj = self.pool.get('ir.model.data')
                        menu_ref = mod_obj.get_object_reference(cr, SUPERUSER_ID, 'epps_company_rules',
                                                                   'epps_company_rules_my_files')
                        menu_id = menu_ref and [menu_ref[1]] or False
                        menu_action_ref = mod_obj.get_object_reference(cr, SUPERUSER_ID, 'epps_company_rules',
                                                                          'epps_company_rules_my_files_action')
                        action_id = menu_action_ref and [menu_action_ref[1]] or False

                        if action_id:
                            v += "&action=" + str(action_id[0])
                        if menu_id:
                            v += "&menu_id=" + str(menu_id[0])

                    else:
                        menu_obj = project_obj.menu_id
                        if menu_obj:
                            menu_id = menu_obj.id
                            if menu_obj.action:
                                action_id = menu_obj.action.id
                                v += "&action=" + str(action_id)
                            v += "&menu_id=" + str(menu_id)

                if web_url and menu_id and action_id:
                    _file_url = web_url + "/web#id=" + str(file.res_id) + "&view_type=form&model=project.project" + v + "&tab=3&fileid=" + str(file.id)
                    try:
                        context['file_url'] = _file_url
                    except Exception:
                        # try to fix "NotImplementedError: 'update' not supported on frozendict" error
                        context = dict(context)
                        context.update({'file_url': _file_url})
                        pass

            res = super(IrAttachment, self).write(cr, uid, ids, vals, context=context)
            if vals.get('document_status_id'):
                dfs_obj = self.pool.get('document.file.status')
                status = dfs_obj.browse(cr,uid, vals.get('document_status_id'),context=context)
                if status.state == 'done':
                    for document in self.browse(cr, uid, ids, context=context):
                        for user in document.notify_user_ids:
                            try:
                                # check if user wants to recive email for document change
                                check_user_settings = self.check_user_settings(cr, SUPERUSER_ID, user.id, context=context)
                                if check_user_settings:
                                    user_obj = self.pool.get('res.users')
                                    # update context with user so we can access user obj on template and use it for mail address
                                    # update context with current user so we know who is the sennder.
                                    context.update({'current_user': user_obj.browse(cr, SUPERUSER_ID, [uid], context=context),
                                                    'user': user_obj.browse(cr, SUPERUSER_ID, [user.id], context=context),
                                                    'template_xml_id':'email_temp_documents_change'})
                                    self.send_mail(cr, SUPERUSER_ID, document.id, context=context)
                            except Exception:
                                pass

            if vals.get('send_document_on_save', False) and vals['send_document_on_save'] == 'on':
                for document in self.browse(cr, uid, ids, context=context):
                    document_next_reviewer_id = document.document_next_reviewer_id and document.document_next_reviewer_id.id or False
                    if vals.get('document_next_reviewer_id', False):
                        document_next_reviewer_id = vals['document_next_reviewer_id']
                    if document_next_reviewer_id:
                        try:
                            # check if user wants to recive email for document change
                            check_user_settings = self.check_user_settings(cr, SUPERUSER_ID, document_next_reviewer_id, context=context)
                            if check_user_settings:
                                user_obj = self.pool.get('res.users')
                                # update context with user so we can access user obj on template and use it for mail address
                                # update context with current user so we know who is the sennder.
                                context.update({'current_user': user_obj.browse(cr, SUPERUSER_ID, [uid], context=context),
                                                'user': user_obj.browse(cr, SUPERUSER_ID, [document_next_reviewer_id], context=context),
                                                'template_xml_id':'email_temp_document_next_reviewer_id'})
                                self.send_mail(cr, SUPERUSER_ID, document.id, context=context)
                        except Exception:
                            pass
        return res

    def check_user_settings(self, cr, uid, id, context=None):
        #check if user wants to recive an email or not
        #return True  # uncomment for testing
        user_obj = self.pool.get('res.users')
        users = user_obj.browse(cr, uid, [id], context=context)
        for user in users:
            if user.documents_change:
                return True
            else:
                return False

    def send_mail(self, cr, uid, id, context=None):
        # find template 'email_temp_message_liked' (defined in xml) and send mail
        ir_model_data = self.pool.get('ir.model.data')
        template_pool = self.pool.get('email.template')
        template_id = False
        model, template_id = ir_model_data.get_object_reference(cr, uid, 'epps_project', context['template_xml_id'])
        template_pool.send_mail(cr, SUPERUSER_ID, template_id, id, force_send=True, raise_exception=False, context=context)
        return True

    def _file_write(self, cr, uid, value):
        bin_value = value.decode('base64')
        fname, full_path = self._get_path(cr, uid, bin_value)
        if not os.path.exists(full_path):
            try:
                with open(full_path, 'wb') as fp:
                    fp.write(bin_value)
            except IOError:
                _logger.exception("_file_write writing %s", full_path)

                # vals={'file_token': uuid.uuid4().hex}
                #self.write(cr,uid,id,vals,context={})
        return fname

    def copy(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        if not default.get('name', False):
            name = self.read(cr, uid, [id], ['name'])[0]['name']
            filename, file_extension = os.path.splitext(name)
            default.update(name=_("%s(copy)%s") % (filename, file_extension))
        default.update(file_token=uuid.uuid4().hex)

        file = self.browse(cr, uid, id, context=context)
        if file.datas:
            _store_fname = self._file_write(cr, uid, file.datas)
            default.update(store_fname=_store_fname)

        return super(IrAttachment, self).copy(cr, uid, id, default, context=context)

    # def copy(self, cr, uid, id, default=None, context=None):
    # if not default:
    #         default = {}
    #     if 'name' not in default:
    #         name = self.read(cr, uid, [id], ['name'])[0]['name']
    #         default.update(name=_("%s (copy)") % (name))
    # return super(IrAttachment, self).copy(cr, uid, id, default,
    # context=context)
    
    def unlink_document(self, cr, uid, ids, context=None):

        if not self.user_can_delete(cr, uid, ids, context=context):
            raise exceptions.Warning(_("You do not have sufficient privileges to delete this file."))
            return
        vals={'file_active': False}
        self.write(cr,uid,ids,vals,context=context)

    def download_and_tag(self, cr, uid, file_token, url, context=None):
        # get current file by tag
        file_id = self.search(cr, uid, [('file_token', '=', file_token)])
        response = urllib2.urlopen(url)
        rr = response.read()
        new_file_content = base64.b64encode(rr)
        _store_fname = self._file_write(cr, uid, new_file_content)
        file = self.browse(cr, uid, file_id[0], context=context)

        # set old record as inactive
        self.write(cr, uid, [file.id], {'file_active': False}, context=context)

        def rreplace(s, old, new, occurrence):
            li = s.rsplit(old, occurrence)
            return new.join(li)

        default = {}

        filename, file_extension = os.path.splitext(file.name)
        olde = '_e' + str(file.file_edition) + '_'
        newe = '_e' + str(file.file_edition + 1) + '_'
        if file.file_edition == 0:
            _name = '' + filename + newe + file_extension
        else:
            _name = rreplace(filename, olde, newe, 1) + file_extension
        default.update(name=_name)

        default.update(file_token=uuid.uuid4().hex)
        default.update(file_edition=file.file_edition + 1)
        default.update(store_fname=_store_fname)
        default.update(file_active=True)

        return super(IrAttachment, self).copy(cr, uid, file_id[0], default, context=context)


    def update_existing_attachment(self, cr, uid, fid, data, date, fp, context=None):
        _store_fname = self._file_write(cr, uid, data)
        file = self.browse(cr, uid, fid, context=context)

        default = {}
        default.update(name=file.name)
        default.update(file_token=uuid.uuid4().hex)
        default.update(file_edition=file.file_edition + 1)
        default.update(store_fname=_store_fname)
        # default.update(ref_id=file.id)
        default.update(file_active=True)
        default.update(file_subversion=file.file_subversion + 1)

        new_file = super(IrAttachment, self).copy(cr, uid, fid, default, context=context)

        self.follow_file(cr, uid, new_file)

        # set correct date on new file to make sure Dropbox sync will work
        epoch = int(date.strftime("%s"))
        os.utime(fp, (epoch, epoch))

        # set old record as inactive
        self.write(cr, uid, [file.id], {'file_active': False, 'ref_id': new_file}, context=context)

    # prepare vals for new_attachment
    def prepare_attachment_vals(self, cr, uid, fid, name, data, context=None):
        _store_fname = self._file_write(cr, uid, data)
        vals = {'name': name, 'file_token': uuid.uuid4().hex, 'store_fname': _store_fname, 'file_active': True,
                'parent_id': fid}
        return vals
    # insert_new_attachment(cr, uid, d.id, md.name, new_file_content)
    def insert_new_attachment(self, cr, uid, fid, name, data, context=None):
        vals = self.prepare_attachment_vals(cr, uid, fid, name, data, context=context)
        #print (vals)
        n_fid = self.create(cr, uid, vals, context=None)
        self.follow_file(cr, uid, n_fid)
        return n_fid

    def docxmerge(self, fname, kp, newfname, logo_file_path):
        fls_lst = []
        fls_lst.append("word/document.xml")
        fls_lst.append("word/footer1.xml")
        fls_lst.append("word/footer2.xml")
        fls_lst.append("word/footer3.xml")
        fls_lst.append("word/footer4.xml")
        fls_lst.append("word/footer5.xml")
        fls_lst.append("word/header1.xml")
        fls_lst.append("word/header2.xml")
        fls_lst.append("word/header3.xml")
        fls_lst.append("word/header4.xml")
        fls_lst.append("word/header5.xml")
        self.docxmerge_e(fname, kp, newfname, logo_file_path, fls_lst)

    def docxmerge_footer(self, fname, kp, newfname):
        fls_lst = []
        fls_lst.append("word/footer1.xml")
        fls_lst.append("word/footer2.xml")
        fls_lst.append("word/footer3.xml")
        fls_lst.append("word/footer4.xml")
        fls_lst.append("word/footer5.xml")
        self.docxmerge_e(fname, kp, newfname, None, fls_lst)

    def docxmerge_e(self, fname, kp, newfname, logo_file_path, fls_lst):
        zfile = zipfile.ZipFile(fname)
        # filexml = read_docx(fname)
        # my_etree = etree.fromstring(filexml)
        fls = []


        zout = zipfile.ZipFile(newfname, 'w')

        def check_element_is(element, type_char):
            word_schema = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
            return element.tag == '{%s}%s' % (word_schema, type_char)

        def replace_hash(kp, input_string):
            for key, value in kp.items():
                if key and key in input_string:
                    return value

        for item in zfile.infolist():
            buffer = zfile.read(item.filename)
            if item.filename in fls_lst:
                print "item.filename:" + item.filename
                # print '++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++'
                # print item.filename
                a = zfile.read(item.filename)
                print a
                # fls.append(a)
                tr = etree.fromstring(a)
                for node in tr.iter(tag=etree.Element):
                    if check_element_is(node, 'fldChar'):
                        print "OK node:"
                        if node.getparent().getnext() and node.getparent().getnext().getchildren() and len(
                                node.getparent().getnext().getchildren()) > 0:
                            print node.getparent().getnext().getchildren()[0].text
                            if len(node.getparent().getnext().getchildren()) > 1:
                                print node.getparent().getnext().getchildren()[1].text
                            # val = node.getparent().getnext().getchildren()[1].text
                            if node.get(
                                    '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}fldCharType') == "begin":
                                node_name = node.getparent().getnext().getchildren()[0].text
                                if not node_name and len(node.getparent().getnext().getchildren()) > 1:
                                    node_name = node.getparent().getnext().getchildren()[1].text

                                node_name = node_name.replace("DOCPROPERTY", "")
                                node_name = node_name.replace("\"", "")
                                node_name = node_name.replace(" ", "")
                                node_name = node_name.replace("\*MERGEFORMAT", "")
                                node_name = node_name.lower()
                                print "OK 1:" + node_name


                            # Now, we're looking for this attribute: w:fldCharType="separate"
                            if node.get(
                                    '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}fldCharType') == "separate":
                                if len(node.getparent().getnext().getchildren()) > 0:
                                    #node_value = node.getparent().getnext().getchildren()[1].text
                                    if node_name:
                                        node_name2 = node_name.replace("DOCPROPERTY", "")
                                        node_name2 = node_name2.replace("\"", "")
                                        node_name2 = node_name2.replace(" ", "")
                                        node_name2 = node_name2.replace("\*MERGEFORMAT", "")
                                        node_name2 = node_name2.lower()
                                        print "OK 2: " + node_name2

                                        if node_name2:
                                            #print ('replace_hash')
                                            rh = replace_hash(kp, node_name2)
                                            # print "--" + node_name2 + "--"
                                            #print "rh"
                                            #print rh
                                            cnt = 0
                                            for neighbor in node.getparent().getnext().iter(
                                                    "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"):
                                                print ('neighbor')
                                                print neighbor.text
                                                if rh:
                                                    cnt += 1
                                                    if cnt == 1:
                                                        neighbor.text = rh
                                                    else:
                                                        neighbor.text = ""
                    elif check_element_is(node, 'fldSimple'):  #Once we've hit this, we're money...
                        node_value = node.getchildren()[0].getchildren()[0].text
                        if node_value:
                            node_value = node_value.lower()
                            node.getchildren()[0].getchildren()[0].text = replace_hash(kp, node_value)
                zout.writestr(item.filename, etree.tostring(tr, encoding='utf8', method='xml'))
            else:
                # replace company logo
                if logo_file_path and item.filename == "word/media/image1.jpg":
                    #print logo_file_path
                    fl = open(logo_file_path, 'r')
                    tr = fl.read()
                    zout.writestr(item, tr)
                else:
                    zout.writestr(item, buffer)
        zout.close()
        zfile.close()
        return 0

    def create_new_file(self, cr, uid, name, parent_id, context=None):
        # get empty file template
        mod_obj = self.pool.get('ir.model.data')
        result = mod_obj.get_object_reference(cr, uid, 'epps_project', 'epps_new_file_template')
        file_template = self.pool.get('ir.attachment').browse(cr, SUPERUSER_ID, result[1])

        if not file_template:
            raise Warning(_('Template file is missing.'))
        _name = name
        _dname = name + ".docx"

        pr = self.pool.get('document.directory').browse(cr, uid, parent_id)

        vals = {'name': _dname,
                'file_edition': 0,
                'file_version': 0,
                'file_subversion': 0,
                'datas_fname': _dname,
                'datas': file_template.datas,
                'type': 'binary',
                'file_active': True,
                'res_id': pr.ressource_id,
                'parent_id': parent_id,
                'file_size': file_template.file_size
                }
        n_fid = self.create(cr, uid, vals)
        self.follow_file(cr, uid, n_fid)
        return n_fid

    def create_new_url_file(self, cr, uid, name, _url, parent_id, context=None):
        _name = name
        pr = self.pool.get('document.directory').browse(cr, uid, parent_id)
        default = {}
        default.update(name=_name)
        default.update(file_token=uuid.uuid4().hex)
        default.update(file_edition=0)
        default.update(file_version=0)
        default.update(file_subversion=0)
        default.update(datas_fname=_name)
        default.update(type="url")
        default.update(url=_url)
        default.update(file_active=True)
        # default.update(res_model="project.project")
        default.update(res_id=pr.ressource_id)
        default.update(parent_id=parent_id)
        n_fid = self.create(cr, uid, default)
        self.follow_file(cr, uid, n_fid)
        return n_fid

    def create_new_version(self, cr, uid, fid, context=None):
        # get current file by id
        file_id = self.search(cr, uid, [('id', '=', fid)])
        file = self.browse(cr, uid, file_id[0], context=context)
        if file.datas:
            filecontent = file.datas.decode('base64')
            filename_original, file_extension = os.path.splitext(file.name)

            dwa_fields_ids = self.pool.get('dwa.fields').search(cr, uid, [])
            dwa_fields = self.pool.get('dwa.fields').browse(cr, uid, dwa_fields_ids)
            fname, full_path = self._get_path(cr, uid, filecontent)
            change_vals = {}

            _version = "V" + str(file.file_version) + "." + str(file.file_subversion)
            _version_fname = "_v_" + str(file.file_version) + "_" + str(file.file_subversion) + "_"

            # first add some file related values to be replaced
            change_vals.update({"Version": _version})
            change_vals.update({"document_version": _version})
            change_vals.update({"Filename": file.name})
            change_vals.update({"FileWriteDate": file.write_date})
            change_vals.update({"document_date": date.today().strftime("%d. %B. %Y.")})

            # then values from dwa_fields table
            for dwa_field in dwa_fields:
                change_vals.update({dwa_field.name: dwa_field.value})

            path = re.sub('[.]', '', file.store_fname)
            path = path.strip('/\\')
            old_name = os.path.join(self._filestore(cr, uid), path);

            fsn = path

            f1 = fsn[:4] + uuid.uuid4().hex
            f2 = fsn[:4] + uuid.uuid4().hex

            new_fname = f1
            new_fname2 = f2

            n1 = os.path.join(self._filestore(cr, uid), f1);
            n2 = os.path.join(self._filestore(cr, uid), f2);

            # print file.name
            # replace values in file
            self.docxmerge(old_name, change_vals, n1)

            # generate new filename
            filename, file_extension = os.path.splitext(file.name)
            _name = filename + _version_fname + file_extension

            # make a copy of file
            shutil.copy2(n1, n2)

            # update current record with new (updated) file
            self.write(cr, uid, [file.id],
                       {'store_fname': new_fname, 'file_edition': file.file_edition + 1,
                        'file_token': uuid.uuid4().hex},
                       context=context)

            # set default values
            default = {}
            default.update(name=_name)
            default.update(file_token=uuid.uuid4().hex)
            default.update(file_edition=file.file_edition)
            default.update(store_fname=new_fname2)
            default.update(file_active=False)
            default.update(ref_id=file.id)

            # copy file
            return super(IrAttachment, self).copy(cr, uid, file_id[0], default, context=context)

    def get_projects_root_folder(self, cr, uid, context=None):
        return self.pool.get('document.directory').search(cr, SUPERUSER_ID, [('name', '=', 'Projects'),
                                                                    ('ressource_id', '=', 0)])
    def get_dwa_project(self, cr, uid, context=None):
        return self.pool.get('project.project').search(cr, SUPERUSER_ID, [('is_company_rules', '=', True)])

    def get_repo_root_folder(self, cr, uid, context=None):
        pr = self.get_projects_root_folder(cr, uid)
        return self.pool.get('document.directory').search(cr, SUPERUSER_ID, [('name', '=', 'Repository'),
                                                                    ('parent_id', '=', pr)])

    def get_my_files_folder(self, cr, uid, context=None):
        pr = self.get_projects_root_folder(cr, uid)
        prid = self.pool.get('project.project').search(cr, SUPERUSER_ID, [('is_my_files', '=', True)])
        return self.pool.get('document.directory').search(cr, SUPERUSER_ID, [('ressource_id', '=', prid[0]),
                                                                             ('parent_id', '=', pr)])

    def get_dwa_root_folder(self, cr, uid, context=None):
        projects_folder = self.get_projects_root_folder(cr, uid, context)
        cr_proj = self.get_dwa_project(cr, uid, context)
        if cr_proj:
            project_folder = self.pool.get('document.directory').search(cr, SUPERUSER_ID,
                                                                        [('ressource_id', '=', cr_proj[0]),
                                                                                  ('parent_id', '=',
                                                                                   projects_folder[0])])
            if project_folder:
                return project_folder[0]
            else:
                #Create the Company rules directory
                model_data = self.pool.get('ir.model.data')
                user_id = model_data.get_object(cr, uid, 'base', 'user_customer_administrator').id
                if user_id:
                    vals = {'name': _('Company Rules'),
                            'directory_active': True,
                            'ressource_id': cr_proj[0],
                            'parent_id': projects_folder[0],
                            'user_id': user_id,
                            }
                    return self.pool.get('document.directory').create(cr, SUPERUSER_ID, vals)



                # http://127.0.0.1:30020/webdav/provisioning2/Documents/Projects/nx/001.jpg

    def calculate_webdav_url(self, cr, uid, fid, context=None):
        file = self.browse(cr, SUPERUSER_ID, fid)
        prj = self.get_projects_root_folder(cr, uid, context)
        retArr = []
        current_folder = file.parent_id.id
        _file_in_structure = False

        # retArr.insert(0, {'name': fold.name, 'id': fold.id, 'type': 0})

        while True:
            if current_folder:
                c_folder = self.pool.get('document.directory').browse(cr, SUPERUSER_ID, current_folder)
                if c_folder.parent_id:
                    current_folder = c_folder.parent_id.id
                else:
                    current_folder = None
                retArr.insert(0, {'name': c_folder.name})
            else:
                break
        path = "/webdav/" + cr.dbname + "/"
        for it in retArr:
            path += it['name'] + "/"
        path += file.name
        print ("path")
        print (path)
        return path

    def calculate_breadcrums_fold(self, cr, uid, fid, pid, context=None):
        # fold = self.pool.get('document.directory').browse(cr, uid, fid)
        #project = self.pool.get('project.project').browse(cr, uid, pid)
        prj = self.get_projects_root_folder(cr, uid, context)
        if pid:
            project = self.pool.get('project.project').browse(cr, uid, pid)
        retArr = []
        current_folder = fid
        _file_in_structure = False
        #retArr.insert(0, {'name': fold.name, 'id': fold.id, 'type': 0})
        ufid = 0
        users_folder = self.pool.get('document.directory').search(cr, SUPERUSER_ID,
                                                                  [('name', '=', 'Users'), ('ressource_id', '=', 0)],
                                                                  context=context)
        if users_folder:
            ufid = users_folder[0]

        prj_xml_name = None
        imd = self.pool.get('ir.model.data')
        imd_pr_id = imd.search(cr, SUPERUSER_ID, [('res_id', '=', pid), ('model', '=', 'project.project')])
        if imd_pr_id:
            imd_pr_obj = imd.browse(cr, SUPERUSER_ID, int(imd_pr_id[0]), context=context)
            prj_xml_name = imd_pr_obj.name


        while True:
            if current_folder:
                c_folder = self.pool.get('document.directory').browse(cr, SUPERUSER_ID, current_folder)
                # print (c_folder.name)
                # print (c_folder.id)
                # print (c_folder.ressource_id)
                # retArr.append()
                if c_folder.id == prj[0] or c_folder.id == ufid:
                    _file_in_structure = True
                    break
                current_folder = c_folder.parent_id.id
                folder_xml_name = None
                imd_fo_id = imd.search(cr, SUPERUSER_ID,
                                       [('res_id', '=', c_folder.id), ('model', '=', 'document.directory')])
                if imd_fo_id:
                    print imd_fo_id[0]
                    imd_fo_obj = imd.browse(cr, SUPERUSER_ID, int(imd_fo_id[0]), context=context)
                    folder_xml_name = imd_fo_obj.name
                    print folder_xml_name

                retArr.insert(0, {'name': c_folder.name, 'id': c_folder.id, 'type': 0, 'prj_xml_name': prj_xml_name,
                                  'folder_xml_name': folder_xml_name})
            else:
                break

        if project and project.is_my_files:
            myfid = self.get_my_files_folder(cr, uid, context)
            retArr.insert(0, {'name': "My files", 'id': myfid, 'type': 0})

        return retArr

    def calculate_breadcrums(self, cr, uid, fid, pid, context=None):
        prj = self.get_projects_root_folder(cr, uid, context)

        file = self.browse(cr, SUPERUSER_ID, fid)
        retArr = []
        current_folder = file.parent_id.id
        if pid:
            project = self.pool.get('project.project').browse(cr, uid, pid)

        ufid = 0
        users_folder = self.pool.get('document.directory').search(cr, SUPERUSER_ID,
                                                                  [('name', '=', 'Users'), ('ressource_id', '=', 0)],
                                                                  context=context)
        if users_folder:
            ufid = users_folder[0]

        prj_xml_name = None
        file_xml_name = None

        _file_in_structure = False
        imd = self.pool.get('ir.model.data')
        imd_pr_id = imd.search(cr, SUPERUSER_ID, [('res_id', '=', pid), ('model', '=', 'project.project')])
        if imd_pr_id:
            imd_pr_obj = imd.browse(cr, SUPERUSER_ID, int(imd_pr_id[0]), context=context)
            prj_xml_name = imd_pr_obj.name

        imd_f_id = imd.search(cr, SUPERUSER_ID, [('res_id', '=', fid), ('model', '=', 'ir.attachment')])
        if imd_f_id:
            imd_f_obj = imd.browse(cr, SUPERUSER_ID, int(imd_f_id[0]), context=context)
            file_xml_name = imd_f_obj.name

        retArr.insert(0, {'name': file.name, 'id': file.id, 'type': 1, 'prj_xml_name': prj_xml_name,
                          'file_xml_name': file_xml_name})

        while True:
            if current_folder:
                c_folder = self.pool.get('document.directory').browse(cr, SUPERUSER_ID, current_folder)
                if c_folder.id == prj[0] or c_folder.id == ufid:
                    _file_in_structure = True
                    break
                current_folder = c_folder.parent_id.id
                folder_xml_name = None
                imd_fo_id = imd.search(cr, SUPERUSER_ID,
                                       [('res_id', '=', c_folder.id), ('model', '=', 'document.directory')])
                if imd_fo_id:
                    imd_fo_obj = imd.browse(cr, SUPERUSER_ID, int(imd_fo_id[0]), context=context)
                    folder_xml_name = imd_fo_obj.name

                retArr.insert(0, {'name': c_folder.name, 'id': c_folder.id, 'type': 0, 'prj_xml_name': prj_xml_name,
                                  'folder_xml_name': folder_xml_name})
            else:
                break

        if project and project.is_my_files:
            myfid = self.get_my_files_folder(cr, uid, context)
            retArr.insert(0, {'name': "My files", 'id': myfid, 'type': 0})

        return retArr

    def copy_repo_2_dwa(self, cr, uid, context=None):
        dwa_folder = self.get_dwa_root_folder(cr, uid, context)
        repo_folder = self.get_repo_root_folder(cr, uid, context)

        mod_obj = self.pool.get('ir.model.data')
        result = mod_obj.get_object_reference(cr, uid, 'epps_company_rules', 'epps_company_rules_project')
        company_rules_project_id = result and result[1] or False
        res_id = company_rules_project_id
        if res_id:
            context['res_id'] = res_id
        if repo_folder:
            folder_ids = self.pool('document.directory').search(cr, uid,
                                                                [('to_company_rules', '=', True),
                                                                 ('parent_id', '!=', dwa_folder)])
            for folder in folder_ids:
                res_id = self.pool('document.directory').copy_sync(cr, uid, folder,
                                                     default={'parent_id': dwa_folder, 'to_company_rules': False},
                                                     context=context)
        return res_id
    def apply_dwa_2_dwa_folder(self, cr, uid, context=None):
        dwa_folder = self.get_dwa_root_folder(cr, uid, context)
        if dwa_folder:
            #return self.apply_dwa_2_folder(cr, uid, dwa_folder, dwa_folder, context)
            return self.apply_dwa_2_folder_structure(cr, uid, dwa_folder, context)

    def apply_dwa_2_repo(self, cr, uid, context=None):
        repo_folder = self.get_repo_root_folder(cr, uid, context)
        dest = self.get_dwa_root_folder(cr, uid, context)
        if repo_folder:
            return self.apply_dwa_2_folder(cr, uid, repo_folder, dest, context)

    #Update the whole folder structure
    def apply_dwa_2_folder_structure(self, cr, uid, src_folder, context=None):
        folid = self.pool('document.directory').search(cr, SUPERUSER_ID, [('parent_id', '=', src_folder), ('directory_active', '=', True)],
                            context=context)
        #apply changes to the docx files
        self.apply_dwa_2_folder(cr, uid, src_folder, src_folder, context)
        if folid:
            for fid in folid:
                self.apply_dwa_2_folder_structure(cr, uid, fid, context=context)

    def apply_dwa_2_folder(self, cr, uid, src_folder, dest_folder, context=None):
        projects_folder = self.get_projects_root_folder(cr, uid, context)
        # print projects_folder
        cr_proj = self.get_dwa_project(cr, uid, context)

        # print cr_proj
        # print project_folder
        # print src_folder
        dwa_fields_ids = self.pool.get('dwa.fields').search(cr, uid, [])
        dwa_fields = self.pool.get('dwa.fields').browse(cr, uid, dwa_fields_ids)
        logo_file_path = ''

        # strip whitespaces from field names
        for dwa_field in dwa_fields:
            dwa_field.name = dwa_field.name.strip()

        # extract logo path
        for dwa_field in dwa_fields:
            if dwa_field.deletable == 0 and dwa_field.ir_att_id > 0 and dwa_field.name == "Company logo":
                logo_id = dwa_field.ir_att_id
                logo_o = self.browse(cr, uid, logo_id)
                path = re.sub('[.]', '', logo_o.store_fname)
                path = path.strip('/\\')
                logo_file_path = os.path.join(self._filestore(cr, uid), path);
                break
        # insert_new_attachment
        if src_folder:
            repo_file_ids = self.search(cr, uid, [('parent_id', '=', src_folder), ('file_active', '=', True),
                                                  ('type', '=', 'binary')])
            # print 'repo_file_ids'
            # print repo_file_ids
            # print src_folder[0]
            for fid in repo_file_ids:
                file = self.browse(cr, uid, fid, context=context)

                # generate new filename
                filename, file_extension = os.path.splitext(file.name)
                _name = filename + file_extension
                if not file_extension or file_extension.lower() != ".docx":
                    continue
                else:
                    _verMaj = file.file_version
                    _verMin = file.file_subversion

                    # find next available subversion (in case file exists)
                    while True:
                        exist_id = self.search(cr, uid, [('parent_id', '=', dest_folder),
                                                         ('name', '=', _name),
                                                         ('file_version', '=', _verMaj),
                                                         ('file_subversion', '=', _verMin),
                                                         #('document_status_id', '=', file.document_status_id.id),
                        ])
                        if not exist_id:
                            break
                        _verMin += 1

                    change_vals = {}
                    _version = "V " + str(_verMaj) + "." + str(_verMin)

                    # first add some file related values to be replaced
                    change_vals.update({"version": _version})
                    change_vals.update({"document_version": _version})
                    change_vals.update({"date": date.today().strftime("%d. %B. %Y.")})
                    change_vals.update({"document_date": date.today().strftime("%d. %B. %Y.")})
                    change_vals.update({"filename": file.name})
                    change_vals.update({"fileWriteDate": file.write_date})
                    #change_vals.update({"fileState": file.document_status_id})

                    # then values from dwa_fields table
                    for dwa_field in dwa_fields:
                        change_vals.update({dwa_field.name.replace(" ", "").lower(): dwa_field.value})

                    path = re.sub('[.]', '', file.store_fname)
                    path = path.strip('/\\')
                    old_name = os.path.join(self._filestore(cr, uid), path);

                    fsn = path

                    f1 = fsn[:4] + uuid.uuid4().hex
                    f2 = fsn[:4] + uuid.uuid4().hex

                    new_fname2 = f2

                    n1 = os.path.join(self._filestore(cr, uid), f1);
                    n2 = os.path.join(self._filestore(cr, uid), f2);

                    # replace values in file
                    self.docxmerge(old_name, change_vals, n1, logo_file_path)

                    # make a copy of file
                    shutil.copy2(n1, n2)

                    if not exist_id:
                        # create new file
                        default = {}
                        default.update(name=_name)
                        default.update(file_token=uuid.uuid4().hex)
                        if hasattr(file, 'file_edition'):
                            default.update(file_edition=file.file_edition)
                        default.update(file_version=_verMaj)
                        default.update(file_subversion=_verMin)
                        default.update(store_fname=new_fname2)
                        if hasattr(file, 'datas_fname'):
                            default.update(datas_fname=file.datas_fname)
                        if hasattr(file, 'mimetype'):
                            default.update(mimetype=file.mimetype)
                        if hasattr(file, 'file_type'):
                            default.update(file_type=file.file_type)
                        default.update(file_active=True)
                        #default.update(res_model="project.project")
                        default.update(res_id=cr_proj[0])
                        default.update(parent_id=dest_folder)
                        i = self.create(cr, uid, default)

                        # disable old (current) file
                        if not src_folder == self.get_repo_root_folder(cr, uid, context):
                            self.write(cr, uid, file.id, {'file_active': False, 'ref_id': i}, context=context)
        return 42
        
    def validate_dwa_fields(self, cr, uid, context=None):
        dwa_fields_ids = self.pool.get('dwa.fields').search(cr, uid, [])
        dwa_fields = self.pool.get('dwa.fields').browse(cr, uid, dwa_fields_ids)
        for dwa_field in dwa_fields:
            if not dwa_field.value:
                raise osv.except_osv(_('Warning !'), _( dwa_field.name + ' value must not be empty.'))
        return True

    def replace_company_logo_and_name(self, cr, uid, context=None):
        dwa_fields_ids = self.pool.get('dwa.fields').search(cr, uid, [])
        dwa_fields = self.pool.get('dwa.fields').browse(cr, uid, dwa_fields_ids)
        logo_id = 0
        company_name = ''
        image = None
        for dwa_field in dwa_fields:
            if dwa_field.name == "Company logo" and dwa_field.deletable == 0:
                logo_id = dwa_field.ir_att_id
                if logo_id:
                    datas = self.pool.get('ir.attachment').read(cr, uid, logo_id)
                    if len(datas):
                        # if there are several, pick first
                        datas = datas[0]
                        fname = str(datas['datas_fname'])
                        ext = fname.split('.')[-1].lower()
                        if ext in ('jpg','jpeg', 'png'):
                            image = datas['datas']
                else:
                    raise osv.except_osv(_('Warning !'), _('You must pick a logo.'))

            elif dwa_field.name == "Organization_name" and dwa_field.deletable == 0:
                company_name = dwa_field.value
                if not company_name:
                    raise osv.except_osv(_('Warning !'), _('Organization name must not be empty.'))

            elif not dwa_field.value:
                raise osv.except_osv(_('Warning !'), _( dwa_field.name + ' value must not be empty.'))
        if company_name and logo_id:
            company = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id
            company.sudo().write({'logo': image, 'name': company_name})
        return True

    def update_company_logo(self, cr, uid, fid, context=None):
        dwa_fields_ids = self.pool.get('dwa.fields').search(cr, uid, [])
        dwa_fields = self.pool.get('dwa.fields').browse(cr, uid, dwa_fields_ids)
        logo_id = 0
        for dwa_field in dwa_fields:
            if dwa_field.name == "Company logo" and dwa_field.deletable == 0:
                logo_id = dwa_field.id
                self.pool.get('dwa.fields').write(cr, uid, logo_id, {'ir_att_id': fid}, context=context)
                break
        return logo_id



    def revert_version(self, cr, uid, fid, context=None):
        # get file to be reverted to
        file_id = self.search(cr, uid, [('id', '=', fid)])
        file = self.browse(cr, uid, file_id[0], context=context)
        ref_file_id = file.ref_id.id
        ofile = self.browse(cr, uid, ref_file_id, context=context)

        # link files to new "head" and make them inactive
        existing_ref_ids = self.search(cr, uid, ['|', ('ref_id', '=', ref_file_id), ('id', '=', ref_file_id)])
        if existing_ref_ids:
            for erf in existing_ref_ids:
                self.write(cr, uid, erf, {'ref_id': file.id, 'file_active': False}, context=context)

        # add timestamp to old "Head" file
        filename, file_extension = os.path.splitext(ofile.name)
        if not filename[-10:].isdigit():
            _name = filename + str(int(time.time())) + file_extension
            self.write(cr, uid, [ref_file_id],
                       {'name': _name},
                       context=context)

        filename, file_extension = os.path.splitext(file.name)
        # remove timestamp from current file
        _name = filename + file_extension
        if filename[-10:].isdigit():
            _name = filename[:-10] + file_extension

        # update current file, make it active and remove reference; i.e. make it "Head" file
        self.write(cr, uid, [file.id],
                   {'ref_id': None, 'name': _name, 'file_active': True, 'file_token': uuid.uuid4().hex},
                   context=context)


    def download_and_overwrite(self, cr, uid, file_token, url, context=None):
        # get current file by tag
        file_id = self.search(cr, uid, [('file_token', '=', file_token)])
        response = urllib2.urlopen(url)
        rr = response.read()
        new_file_content = base64.b64encode(rr)
        _store_fname = self._file_write(cr, uid, new_file_content)

        file = self.browse(cr, uid, file_id[0], context=context)
        nold = os.path.join(self._filestore(cr, uid), file.store_fname)
        print "download_and_overwrite"

        file_ver = file.file_prev_version
        file_subver = file.file_prev_subversion
        # path = re.sub('[.]', '', file.store_fname)
        # path = path.strip('/\\')
        #
        # new_fname = path[:4] + uuid.uuid4().hex
        #
        #
        # n1 = os.path.join(self._filestore(cr, uid), _store_fname);
        # n2 = os.path.join(self._filestore(cr, uid), new_fname);
        # _store_fname_rev = new_fname
        #
        #
        # # make a copy of file
        # shutil.copy2(n1, n2)


        # save a copy of old file
        if hasattr(file, 'save_revision'):
            if file.save_revision:
                # create new unactive file revision; we need to change name due to constraints
                filename, file_extension = os.path.splitext(file.name)
                _name = filename + str(int(time.time())) + file_extension
                # _version = "V" + str(file.file_version) + "." + str(file.file_subversion)
                #
                # change_vals = {}
                # change_vals.update({"Version": _version})
                # change_vals.update({"document_version": _version})
                # change_vals.update({"Filename": file.name})
                # change_vals.update({"FileWriteDate": file.write_date})
                # change_vals.update({"document_date": date.today().strftime("%d. %B. %Y.")})
                #
                # path = re.sub('[.]', '', _store_fname)
                # path = path.strip('/\\')
                # old_name = os.path.join(self._filestore(cr, uid), path);
                #
                # fsn = path

                # f1 = fsn[:4] + uuid.uuid4().hex

                # n1 = os.path.join(self._filestore(cr, uid), f1);

                # replace values in file
                # self.docxmerge_footer(old_name, change_vals, n1)

                default = {}
                default.update(name=_name)
                default.update(file_active=False)
                default.update(file_version=file_ver)
                default.update(file_subversion=file_subver)
                default.update(file_token=uuid.uuid4().hex)
                default.update(ref_id=file.id)
                nfid = super(IrAttachment, self).copy(cr, uid, file.id, default, context=context)
                self.write(cr, uid, [nfid], {'ref_id': file.id, 'file_version': file_ver}, context=context)
        filename, file_extension = os.path.splitext(file.name)
        _name = filename + str(int(time.time())) + file_extension
        _version = "V" + str(file.file_version) + "." + str(file.file_subversion)

        change_vals = {}
        change_vals.update({"Version": _version})
        change_vals.update({"document_version": _version})
        change_vals.update({"Filename": file.name})
        change_vals.update({"FileWriteDate": file.write_date})
        change_vals.update({"document_date": date.today().strftime("%d. %B. %Y.")})

        path = re.sub('[.]', '', _store_fname)
        path = path.strip('/\\')
        old_name = os.path.join(self._filestore(cr, uid), path);

        fsn = path

        f1 = fsn[:4] + uuid.uuid4().hex

        n1 = os.path.join(self._filestore(cr, uid), f1);

        # replace values in file
        self.docxmerge_footer(old_name, change_vals, n1)

        file_ver0 = file.file_version
        file_ver1 = file.file_subversion
        # update file
        self.write(cr, uid, [file.id],
                   {'store_fname': _store_fname, 'file_token': uuid.uuid4().hex, 'file_prev_version': file_ver0,
                    'file_prev_subversion': file_ver1}, context=context)

        # delete old file from filesystem
        #os.remove(nold)

        # save revision (copy) if needed
        # if hasattr(file, 'save_revision'):
        #     if file.save_revision:
        #         # create new unactive file revision; we need to change name due to constraints
        #         filename, file_extension = os.path.splitext(file.name)
        #         _name = filename + str(int(time.time())) + file_extension
        #         _version = "V" + str(file.file_version) + "." + str(file.file_subversion)
        #
        #         change_vals = {}
        #         change_vals.update({"Version": _version})
        #         change_vals.update({"document_version": _version})
        #         change_vals.update({"Filename": file.name})
        #         change_vals.update({"FileWriteDate": file.write_date})
        #         change_vals.update({"document_date": date.today().strftime("%d. %B. %Y.")})
        #
        #         path = re.sub('[.]', '', _store_fname)
        #         path = path.strip('/\\')
        #         old_name = os.path.join(self._filestore(cr, uid), path);
        #
        #         fsn = path
        #
        #         f1 = fsn[:4] + uuid.uuid4().hex
        #
        #         n1 = os.path.join(self._filestore(cr, uid), f1);
        #
        #         # replace values in file
        #         self.docxmerge_footer(old_name, change_vals, n1)
        #
        #
        #         default = {}
        #         default.update(name=_name)
        #         default.update(file_token=uuid.uuid4().hex)
        #         default.update(store_fname=f1)
        #         default.update(file_active=False)
        #         default.update(ref_id=file.id)
        #         super(IrAttachment, self).copy(cr, uid, file.id, default, context=context)
        if hasattr(file, 'send_on_save'):
            if file.send_on_save:
                print ('somehow send something to some persons')
        return

    #------------------------------------------------------
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


class DocumentDirectory(osv.osv):
    _name = 'document.directory'
    _description = 'Directory'
    _order = 'name'
    _inherit = ['document.directory', 'mail.thread']
    _columns = {
        'permission_type': fields.selection([('Editor', 'Editor'),
                                             ('Reviewer', 'Reviewer'),
                                             ('Viewer', 'Viewer'),
                                             ('Previewer', 'Previewer'),
                                             ('Uploader', 'Uploader')],
                                            'Invited permission',
                                            copy=False),
        # 'shared_user_ids': fields.many2many('res.users', string='Shared with '),
        'shared_editors_ids': fields.many2many('res.users', 'document_directory_res_users_rel', string='Shared with editors'),
        'shared_reviewers_ids': fields.many2many('res.users', 'document_directory_res_users_shared_reviewers_rel', string='Shared with reviewers'),
        'shared_viewers_ids': fields.many2many('res.users', 'document_directory_shared_viewers_rel', string='Shared with viewers'),
        'shared_previewers_ids': fields.many2many('res.users', 'document_directory_shared_previewers_rel', string='Shared with previewers'),
        'shared_uploaders_ids': fields.many2many('res.users', 'document_directory_shared_uploaders_rel', string='Shared with uploaders'),
        'directory_active': fields.boolean('Active', readonly=True, required=True, default=True),
        'isPrivate': fields.boolean('Private', readonly=True, required=True, default=False),
        'to_company_rules': fields.boolean('To company rules', readonly=True, default=False),
    }


    _defaults = {
        'isPrivate': False,
    }

    _track = {

    }

    _sql_constraints = [('unique_directory_parent_id_name', 'unique(name, parent_id)', 'You can not have 2 directories with the same name')]

    def get_projs_root(self, cr, uid, context=None):
        projs_folder = self.search(cr, SUPERUSER_ID, [('name', '=', 'Projects'), ('ressource_id', '=', 0),
                                                      ('directory_active', '=', True)], context=context)
        # return self.browse(cr, SUPERUSER_ID, projs_folder[0])
        return [(rec.id, rec.name) for rec in self.browse(cr, SUPERUSER_ID, projs_folder[0], context=context)]

    def get_proj_root(self, cr, uid, pid, context=None):
        p = self.pool.get('project.project').browse(cr, SUPERUSER_ID, pid)
        if not p:
            return None
        projs_folder = self.search(cr, SUPERUSER_ID, [('name', '=', 'Projects'), ('ressource_id', '=', 0),
                                                      ('directory_active', '=', True)], context=context)
        proj_folder = self.search(cr, SUPERUSER_ID, [('parent_id', '=', projs_folder[0]), ('ressource_id', '=', pid),
                                                     ('directory_active', '=', True)], limit=1, context=context)
        if not proj_folder:
            #Parent id needs to be the Project directory
            vals = {'name': p.name,
                    'directory_active': True,
                    'ressource_id': pid,
                    'parent_id': projs_folder[0]
                    }
            proj_folder = self.create(cr, uid, vals)
        return [(rec.id, rec.name) for rec in self.browse(cr, SUPERUSER_ID, proj_folder, context=context)]

    def get_my_user_folder(self, cr, uid, context=None):
        """Return '<uid user>' folder as 'Users' child folder, if it doesn't exist, create one."""

        users_folder = self.search(cr, SUPERUSER_ID, [('name', '=', 'Users'), ('ressource_id', '=', 0)], limit=1, context=context)
        if not users_folder:
            vals = {'name': 'Users',
                    'directory_active': True,
                    'ressource_id': 0,
                    'user_id': False,
                    }
            users_folder = [self.create(cr, SUPERUSER_ID, vals)]
            if users_folder:
                self.pool('ir.model.data').create(cr, SUPERUSER_ID, {
                    'name': 'epps_document_users_root',
                    'model': 'document.directory',
                    'module': 'epps_design',
                    'res_id': users_folder[0],
                    'noupdate': True,  # If it's False, target record (res_id) will be removed while module update
                }, context=context)

        u = self.pool.get('res.users').browse(cr, uid, uid)
        #parsing the user login name replaceing "." and "@" with "_"
        _name = self.strip_string_and_lowercase(u.login)
        print u
        print u.login
        print _name
        print users_folder
        myfid = self.search(cr, uid, [('name', '=', _name), ('parent_id', '=', users_folder[0])], limit=1)
        if myfid:
            print(myfid)
            return myfid
        else:
            print('create new user folder')
            vals = {'name': _name,
                    'directory_active': True,
                    'parent_id': users_folder[0],
                    }
            return self.create(cr, uid, vals)
            # project_folder = self.pool.get('document.directory').search(cr, uid, [('ressource_id', '=', cr_proj[0]),
            #                                                                      ('parent_id', '=', projects_folder[0])])
            # print cr_proj
    def strip_string_and_lowercase(self, s):
            sa = unidecode(s).replace('@', '_')
            sa_dot = sa.replace('.', '_')
            #this will "eat" chars sa = s.encode('ascii', 'ignore').lower()
            allowed = string.ascii_lowercase+string.ascii_uppercase +string.digits+'_'+'-'
            return ''.join(c for c in sa_dot if c in allowed)

    def get_all_shared_users(self, cr, uid, fid, default=None, context=None):
        folder_id = self.search(cr, uid, [('id', '=', fid)])
        folder = self.browse(cr, uid, folder_id[0], context=context)
        mergedlist = list(set(folder.shared_editors_ids + folder.shared_reviewers_ids + folder.shared_viewers_ids +
                              folder.shared_previewers_ids + folder.shared_uploaders_ids))
        return mergedlist


    # def copy(self, cr, uid, id, default=None, context=None):
    # if not default:
    #         default ={}
    #     name = self.read(cr, uid, [id])[0]['name']
    #     default.update(name=_("%s (copy)") % (name))
    #     return super(document_directory,self).copy(cr, uid, id, default, context=context)

    def create(self, cr, uid, vals, context=None):
        if not vals.get('parent_id', None) == None:
            if not self.user_can_create(cr, uid, int(vals.get('parent_id', None)), context=context):
                raise exceptions.Warning(_("You do not have sufficient privileges to create new folder."))
                return

        if not vals:
            vals = {}
        _dir_name = vals.get('name', '')
        _parent_id = vals.get('parent_id', None)
        print "Trying to create directory: name: %s with parent_id: %s" %(_dir_name, _parent_id)
        if _dir_name:
            _dir_ids = self.search(cr, SUPERUSER_ID, [('parent_id', '=', _parent_id), ('name', '=', _dir_name)],
                                   context=context)
            if not _dir_ids:
                try:
                    res = super(DocumentDirectory, self).create(cr, uid, vals, context=context)

                    res_obj = self.browse(cr, uid, res, context=context)
                    if res_obj:
                        print "Created directory: name: %s with parent_id: %s" % (res_obj[0].name or '', res_obj[0].parent_id or '')
                    return res
                except Exception, e:
                    _logger.warning(
                        "Unable to create directory name: %s parent_id: %s, this is what we get %s." % (
                        _dir_name, _parent_id, e))
            else:
                print "Found existing directory: name: %s with parent_id: %s" % (_dir_name, _parent_id)
                raise osv.except_osv(_('Warning!'), _('Directory with specified name already exists.'))


    def copy(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        default['user_id'] = uid
        name = self.read(cr, SUPERUSER_ID, [id], ['name'])[0]['name']
        if not default.get('name', False):
            default.update(name=_("%s") % (name,))
        nfold = super(DocumentDirectory, self).copy(cr, uid, id, default, context=context)

        parent_id = self.read(cr, uid, [nfold], ['parent_id'])[0]['parent_id']

        # remove (copy) from copied name
        folder_id = self.search(cr, uid, [('name', '=', name), ('parent_id', '=', parent_id[0])])
        if not folder_id:
            self.write(cr, uid, [nfold], {'name': name}, context=context)

        fids = self.pool.get('ir.attachment').search(cr, SUPERUSER_ID,
                                                     [('parent_id', '=', id), ('file_active', '=', True)],
                                                     context=context)
        if fids:
            for fid in fids:
                df = {}
                df.update(parent_id=nfold)
                file = self.pool.get('ir.attachment').browse(cr, uid, fid, context=context)
                if not file.parent_id.id == nfold:
                    df.update(name=file.name)
                self.pool.get('ir.attachment').copy(cr, uid, fid, df, context=context)

        folid = self.search(cr, SUPERUSER_ID, [('id', '!=', nfold), ('parent_id', '=', id), ('directory_active', '=', True)],
                            context=context)
        if folid:
            for fid in folid:
                df = {'user_id': uid}
                df.update(parent_id=nfold)
                self.copy(cr, uid, fid, df, context=context)

        return nfold

    def write(self, cr, uid, ids, vals, context=None):
        if not self.user_can_write(cr, uid, ids, context=context):
            raise exceptions.Warning(_("You do not have sufficient privileges to write in current folder."))
            return

        res = super(DocumentDirectory, self).write(cr, uid, ids, vals, context)
        return res

    def copy_sync(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        name = self.read(cr, SUPERUSER_ID, [id], ['name'])[0]['name']
        if not default.get('name', False):
            default.update(name=_("%s") % (name,))

        parent_id = default.get('parent_id', None)
        existing_directory = self.pool.get('document.directory').search(cr, SUPERUSER_ID,
                                                                   [('name', '=', name), ('parent_id', '=', parent_id)])
        if existing_directory:
            parent_id = existing_directory[0]
            #print 'Directory ' + name + 'already exists using its id as the parent_id: ' + str(parent_id)

            fids = self.pool.get('ir.attachment').search(cr, SUPERUSER_ID,
                                                         [('parent_id', '=', id), ('file_active', '=', True)],
                                                         context=context)
            if fids:
                for fid in fids:
                    df = {}
                    if context.get('res_id'):
                        df.update(res_id=context.get('res_id'))
                    df.update(parent_id=parent_id)
                    file = self.pool.get('ir.attachment').browse(cr, uid, fid, context=context)
                    existing_file = self.pool.get('ir.attachment').search(cr, SUPERUSER_ID,
                                                             [('parent_id', '=', parent_id),
                                                              ('name', '=', file.name),
                                                              ('file_active', '=', True)],
                                                             context=context)
                    if not existing_file:
                        if not file.parent_id.id == parent_id:
                            df.update(name=file.name)
                        if context.get('res_id'):
                            df.update(res_id=context.get('res_id'))
                        self.pool.get('ir.attachment').copy(cr, uid, fid, df, context=context)
                    else:
                        #print 'file ' + file.name + ' already exists in directory ' + name
                        pass

            folid = self.search(cr, SUPERUSER_ID,
                                [('id', '!=', parent_id), ('parent_id', '=', id), ('directory_active', '=', True)],
                                context=context)
            if folid:
                for fid in folid:
                    defaults = {'parent_id': parent_id}
                    if context.get('res_id'):
                        defaults.update(res_id=context.get('res_id'))
                    self.copy_sync(cr, uid, fid, defaults, context=context)
            return parent_id

        else:
            nfold = super(DocumentDirectory, self).copy(cr, uid, id, default, context=context)

            parent_id = self.read(cr, uid, [nfold], ['parent_id'])[0]['parent_id']

            # remove (copy) from copied name
            folder_id = self.search(cr, uid, [('name', '=', name), ('parent_id', '=', parent_id[0])])
            if not folder_id:
                self.write(cr, uid, [nfold], {'name': name}, context=context)

            fids = self.pool.get('ir.attachment').search(cr, SUPERUSER_ID,
                                                         [('parent_id', '=', id), ('file_active', '=', True)],
                                                         context=context)
            if fids:
                for fid in fids:
                    df = {}
                    df.update(parent_id=nfold)
                    if context.get('res_id'):
                        df.update(res_id=context.get('res_id'))
                    file = self.pool.get('ir.attachment').browse(cr, uid, fid, context=context)
                    if not file.parent_id.id == nfold:
                        df.update(name=file.name)
                    self.pool.get('ir.attachment').copy(cr, uid, fid, df, context=context)

            folid = self.search(cr, SUPERUSER_ID,
                                [('id', '!=', nfold), ('parent_id', '=', id), ('directory_active', '=', True)],
                                context=context)
            if folid:
                for fid in folid:
                    df = {}
                    df.update(parent_id=nfold)
                    if context.get('res_id'):
                        df.update(res_id=context.get('res_id'))
                    self.copy(cr, uid, fid, df, context=context)

            return nfold

    def make_folder_private(self, cr, uid, folder_id):
        context = {}
        folder = self.pool('document.directory').browse(cr, uid, folder_id, context=context)

        # add current user to all roles on private folder
        folder.shared_editors_ids = [(4, uid)]
        folder.shared_reviewers_ids = [(4, uid)]
        folder.shared_viewers_ids = [(4, uid)]
        folder.shared_previewers_ids = [(4, uid)]
        folder.shared_uploaders_ids = [(4, uid)]

        res = self.write(cr, uid, folder_id, {'isPrivate': True}, context=context)
        return res

    def user_can_write(self, cr, uid, folder_id, context=None):
        """Determine if user has right to write/update current folder"""

        # super user can always write
        # if uid == SUPERUSER_ID:
        #    return True

        context = {}
        directoryObj = self.pool('document.directory')
        attachmentObj = self.pool('ir.attachment')
        usersObj = self.pool('res.users')
        prj = attachmentObj.get_projects_root_folder(cr, uid, context)
        user = usersObj.browse(cr, SUPERUSER_ID, uid, context)

        current_folder = folder_id
        _canwrite = True

        # find most restrictive rule in hierarchy
        while True:
            if current_folder:
                c_folder = directoryObj.browse(cr, SUPERUSER_ID, current_folder)
                if not c_folder:
                    break
                if c_folder.id == prj[0]:
                    # we got to the root
                    break
                current_folder = c_folder.parent_id.id
                if c_folder.isPrivate:
                    if not user in c_folder.shared_editors_ids and not user in c_folder.shared_reviewers_ids \
                            and user.id != c_folder.user_id.id:
                        _canwrite = False
                        break
            else:
                break
        return _canwrite

        # 'shared_editors_ids': fields.many2many('res.users', string='Shared with editors'),
        # 'shared_reviewers_ids': fields.many2many('res.users', string='Shared with reviewers'),
        # 'shared_viewers_ids': fields.many2many('res.users', string='Shared with viewers'),
        # 'shared_previewers_ids': fields.many2many('res.users', string='Shared with previewers'),
        # 'shared_uploaders_ids': fields.many2many('res.users', string='Shared with uploaders'),

    def user_can_create(self, cr, uid, folder_id, context=None):
        """Determine if user has right to create new folder"""

        # super user can always create
        # if uid == SUPERUSER_ID:
        #    return True

        context = {}
        directoryObj = self.pool('document.directory')
        attachmentObj = self.pool('ir.attachment')
        usersObj = self.pool('res.users')
        prj = attachmentObj.get_projects_root_folder(cr, uid, context)
        user = usersObj.browse(cr, SUPERUSER_ID, uid, context)

        current_folder = folder_id
        _cancreate = True

        # find most restrictive rule in hierarchy
        while True:
            if current_folder:
                c_folder = directoryObj.browse(cr, SUPERUSER_ID, current_folder)

                if c_folder.id == prj[0]:
                    # we got to the root
                    break
                current_folder = c_folder.parent_id.id
                # if folder.user_id.id == uid:  # owner should have access
                #     return True

                if c_folder.isPrivate:
                    if not user in c_folder.shared_editors_ids and not user in c_folder.shared_uploaders_ids \
                            and not user in c_folder.shared_reviewers_ids and user.id != c_folder.user_id.id:
                        _cancreate = False
                        break
            else:
                break

        return _cancreate

    def user_can_read(self, cr, uid, folder_id, context=None):
        """Determine if user has right to read folder"""

        # super user can always         read
        # if uid == SUPERUSER_ID:
        #    return True

        context = {}
        directoryObj = self.pool('document.directory')
        attachmentObj = self.pool('ir.attachment')
        usersObj = self.pool('res.users')
        prj = attachmentObj.get_projects_root_folder(cr, uid, context)
        user = usersObj.browse(cr, SUPERUSER_ID, uid, context)

        current_folder = folder_id
        _canread = True

        # find most restrictive rule in hierarchy
        while True:
            if current_folder:
                c_folder = directoryObj.browse(cr, SUPERUSER_ID, current_folder)

                if c_folder.id == prj[0]:
                    # we got to the root
                    break
                current_folder = c_folder.parent_id.id

                if c_folder.isPrivate:
                    if not user in c_folder.shared_editors_ids and not user in c_folder.shared_uploaders_ids \
                            and not user in c_folder.shared_reviewers_ids and not user in c_folder.shared_viewers_ids\
                            and user.id != c_folder.user_id.id:
                        _canread = False
                        break
            else:
                break

        return _canread

    def user_can_delete(self, cr, uid, folder_id, context=None):
        """Determine if user has right to delete folder"""

        # super user can always delete
        # if uid == SUPERUSER_ID:
        #    return True

        context = {}
        directoryObj = self.pool('document.directory')
        attachmentObj = self.pool('ir.attachment')
        usersObj = self.pool('res.users')
        prj = attachmentObj.get_projects_root_folder(cr, uid, context)
        user = usersObj.browse(cr, SUPERUSER_ID, uid, context)

        current_folder = folder_id
        _candelete = True

        # find most restrictive rule in hierarchy
        while True:
            if current_folder:
                c_folder = directoryObj.browse(cr, SUPERUSER_ID, current_folder)

                if c_folder.id == prj[0]:
                    # we got to the root
                    break
                current_folder = c_folder.parent_id.id

                if c_folder.isPrivate:
                    if not user in c_folder.shared_editors_ids and user.id != c_folder.user_id.id:
                        _candelete = False
                        break
            else:
                break

        return _candelete

    def share_folder(self, cr, uid, fid, pid, uids, default=None, context=None):
        folder_id = self.search(cr, uid, [('id', '=', fid)])
        folder = self.browse(cr, uid, folder_id[0], context=context)
        if folder and folder.user_id and folder.user_id.id == uid and folder.isPrivate is True:
            if pid == 1:
                puids = [x.id for x in folder.shared_editors_ids]
                for _user_id in uids:
                    if int(_user_id) not in puids:
                        _tid = int(_user_id)
                        folder.shared_editors_ids = [(4, _tid)]
            # This is now Authors
            if pid == 2:
                puids = [x.id for x in folder.shared_reviewers_ids]
                for _user_id in uids:
                    if int(_user_id) not in puids:
                        _tid = int(_user_id)
                        folder.shared_reviewers_ids = [(4, _tid)]
            if pid == 3:
                puids = [x.id for x in folder.shared_viewers_ids]
                for _user_id in uids:
                    if int(_user_id) not in puids:
                        _tid = int(_user_id)
                        folder.shared_viewers_ids = [(4, _tid)]
            # Not used anymore
            if pid == 4:
                puids = [x.id for x in folder.shared_previewers_ids]
                for _user_id in uids:
                    if int(_user_id) not in puids:
                        _tid = int(_user_id)
                        folder.shared_previewers_ids = [(4, _tid)]
            if pid == 5:
                puids = [x.id for x in folder.shared_uploaders_ids]
                for _user_id in uids:
                    if int(_user_id) not in puids:
                        _tid = int(_user_id)
                        folder.shared_uploaders_ids = [(4, _tid)]
        else:
            raise osv.except_osv(_('Warning!'), _('You do not have permission to do this action.'))

    def unshare_folder(self, cr, uid, fid, pid, uids, default=None, context=None):
        folder_id = self.search(cr, uid, [('id', '=', fid)])
        folder = self.browse(cr, uid, folder_id[0], context=context)
        if folder and folder.user_id and folder.user_id.id == uid and folder.isPrivate is True:
            if pid == 0:
                puids = []
                puids = [x.id for x in folder.shared_editors_ids]
                for _user_id in uids:
                    if int(_user_id) in puids:
                        _tid = int(_user_id)
                        folder.shared_editors_ids = [(3, _tid)]

                puids = [x.id for x in folder.shared_reviewers_ids]
                for _user_id in uids:
                    if int(_user_id) in puids:
                        _tid = int(_user_id)
                        folder.shared_reviewers_ids = [(3, _tid)]

                puids = [x.id for x in folder.shared_viewers_ids]
                for _user_id in uids:
                    if int(_user_id) in puids:
                        _tid = int(_user_id)
                        folder.shared_viewers_ids = [(3, _tid)]

                puids = [x.id for x in folder.shared_previewers_ids]
                for _user_id in uids:
                    if int(_user_id) in puids:
                        _tid = int(_user_id)
                        folder.shared_previewers_ids = [(3, _tid)]

                puids = [x.id for x in folder.shared_uploaders_ids]
                for _user_id in uids:
                    if int(_user_id) in puids:
                        _tid = int(_user_id)
                        folder.shared_uploaders_ids = [(3, _tid)]
        else:
            raise osv.except_osv(_('Warning!'), _('You do not have permission to do this action.'))

    def get_directory_subdirectories(self, cr, uid, fid, context=None):
        mod_obj = self.pool('ir.model.data')
        repository_ref = mod_obj.get_object_reference(cr, uid, 'epps_design',
                                                'epps_document_repository_root')
        repository_id = repository_ref and [repository_ref[1]] or False
        if fid and repository_id:
            current_directory = self.browse(cr, uid, fid, context=context)
            if current_directory:
                if current_directory.isPrivate == True:
                    if current_directory.user_id:
                        if uid != current_directory.user_id.id and uid not in\
                                [user_id.id for user_id in current_directory.shared_editors_ids if user_id.id == uid]:
                            return []
                    else:
                        return []

            res_ids = self.search(cr, uid, [ '&',
                                      '&',('id', '!=', repository_id[0]),('parent_id', '=', fid),
                                        ('directory_active', '=', 'true')]
                                , context=context)
            res_obj = self.browse(cr, uid, res_ids, context=context)
            subdirs = []
            for dir in res_obj:
                subdirs.append({'id':dir.id,
                                'name':dir.name,
                                'isPrivate': dir.isPrivate or False})
        return subdirs

    def get_directory_subdirectories_recursively(self, cr, uid, fid, subdirs, context=None):
        mod_obj = self.pool('ir.model.data')
        repository_ref = mod_obj.get_object_reference(cr, uid, 'epps_design',
                                                      'epps_document_repository_root')
        repository_id = repository_ref and [repository_ref[1]] or False
        if fid and repository_id:
            res_ids = self.search(cr, uid, ['&',
                                            '&', ('id', '!=', repository_id[0]), ('parent_id', '=', fid),
                                            ('directory_active', '=', 'true')]
                                  , context=context)
            res_obj = self.browse(cr, uid, res_ids, context=context)
            for dir in res_obj:
                subdirs.append({'id': dir.id,
                                'name': dir.name,
                                'isPrivate': dir.isPrivate or False})
                if dir.child_ids:
                    self.get_directory_subdirectories_recursively(cr, uid, dir.id, subdirs, context=context)
        return subdirs

    def can_upload_file(self, cr, uid, fid, pid, default=None, context=None):
        return self.user_can_read(cr, uid, fid, context=context)

        folder_id = self.search(cr, uid, [('id', '=', fid)])
        folder = self.browse(cr, uid, folder_id[0], context=context)
        p = self.pool.get('project.project').browse(cr, SUPERUSER_ID, pid)

        if not p:
            return False
        if p.is_my_files:
            current_folder = fid
            muf = self.get_my_user_folder(cr, uid, context)[0]
            while True:
                if current_folder:
                    c_folder = self.pool.get('document.directory').browse(cr, SUPERUSER_ID, current_folder)
                    if c_folder.id == muf:
                        return True
                    current_folder = c_folder.parent_id.id
                else:
                    break
            return False

        if folder.isPrivate == True:
            if folder.user_id.id == uid:  # owner should have access
                return True
            for user in folder.shared_editors_ids:
                if uid == user.id:  # editors should have access
                    return True
            for user in folder.shared_reviewers_ids:
                if uid == user.id:  # reviewers should have access
                    return True
            for user in folder.shared_viewers_ids:
                if uid == user.id:  # viewers should have access
                    return True
            for user in folder.shared_previewers_ids:
                if uid == user.id:  # previewers should have access
                    return True
            for user in folder.shared_uploaders_ids:
                if uid == user.id:  # uploaders should have access
                    return True
            return False
        return True

    def get_parent_folder(self, d, node_list):
        if d.parent_id.id:
            node_list.append(d)
            self.get_parent_folder(d.parent_id, node_list)
        else:
            return node_list
        return node_list

    def build_folder_path(self, cr, uid, ids):
        # get current directory
        d = self.browse(cr, SUPERUSER_ID, ids, context={})
        node_list = []
        return self.get_parent_folder(d, node_list)

    def unlink_leaf_directory_files(self, cr, uid, dir_id, context=None):
        """Un-links all the files within the last subdirectory."""
        dir_obj = self.browse(cr, uid, [dir_id], context=context)
        if dir_obj:
            if dir_obj.child_ids:
                for subdir in dir_obj.child_ids:
                    self.unlink_leaf_directory_files(cr, uid, subdir.id, context=context)
            else:
                if dir_obj.file_ids:
                    for file_obj in dir_obj.file_ids:
                        print "Unlinking file id: %s with parent_id: %s" % (file_obj.id or '', dir_obj.id or '')
                        res = file_obj.unlink(context=context)
                        if res:
                            print "File unlinked."
                        else:
                            print "File was not unlinked."
                    return True
        return False

def monkeypatch_method(cls):
    def decorator(func):
        setattr(cls, func.__name__, func)
        return func

    return decorator


@monkeypatch_method(nodes.node_dir)
def _child_get(self, cr, name=None, domain=None):
    dirobj = self.context._dirobj
    uid = self.context.uid
    ctx = self.context.context.copy()
    ctx.update(self.dctx)
    where = [('parent_id', '=', self.dir_id)]
    if name:
        where.append(('name', '=', name))
        is_allowed = self.check_perms(1)
    else:
        is_allowed = self.check_perms(5)

    if not is_allowed:
        raise IOError(errno.EPERM, "Permission into directory denied.")

    if not domain:
        domain = []

    where2 = where + domain + [('ressource_parent_type_id', '=', False)]
    ids = dirobj.search(cr, uid, where2, context=ctx)
    res = []
    for dirr in dirobj.browse(cr, uid, ids, context=ctx):
        klass = dirr.get_node_class(dirr, context=ctx)
        res.append(klass(dirr.name, self, self.context, dirr))

    where += [('file_active', '=', True)]
    fil_obj = dirobj.pool.get('ir.attachment')
    ids = fil_obj.search(cr, uid, where, context=ctx)
    if ids:
        for fil in fil_obj.browse(cr, uid, ids, context=ctx):
            klass = self.context.node_file_class
            res.append(klass(fil.name, self, self.context, fil))
    return res


@monkeypatch_method(nodes.document_storage)
def set_data(self, cr, uid, id, file_node, data, context=None, fil_obj=None):
    """ store the data.
        This function MUST be used from an ir.attachment. It wouldn't make sense
        to store things persistently for other types (dynamic).
    """
    boo = self.browse(cr, uid, id, context=context)
    if fil_obj:
        ira = fil_obj
    else:
        ira = self.pool.get('ir.attachment').browse(cr, uid, file_node.file_id, context=context)

    _logger.debug("Store data for ir.attachment #%d." % ira.id)
    store_fname = None
    fname = None
    filesize = len(data)
    self.pool.get('ir.attachment').write(cr, uid, [file_node.file_id],
                                         {'datas': data.encode('base64'), 'file_token': uuid.uuid4().hex},
                                         context=context)
    # 2nd phase: store the metadata
    try:
        icont = ''
        mime = ira.file_type
        if not mime:
            mime = ""
        try:
            mime, icont = cntIndex.doIndex(data, ira.datas_fname, ira.file_type or None, fname)
        except Exception:
            _logger.debug('Cannot index file.', exc_info=True)
            pass
        try:
            icont_u = ustr(icont)
        except UnicodeError:
            icont_u = ''
        # a hack: /assume/ that the calling write operation will not try
        # to write the fname and size, and update them in the db concurrently.
        # We cannot use a write() here, because we are already in one.
        cr.execute('UPDATE ir_attachment SET file_size = %s, index_content = %s, file_type = %s WHERE id = %s',
                   (filesize, icont_u, mime, file_node.file_id))
        self.pool.get('ir.attachment').invalidate_cache(cr, uid, ['file_size', 'index_content', 'file_type'],
                                                        [file_node.file_id], context=context)
        file_node.content_length = filesize
        file_node.content_type = mime
        return True
    except Exception, e:
        _logger.warning("Cannot save data.", exc_info=True)
        # should we really rollback once we have written the actual data?
        # at the db case (only), that rollback would be safe
        raise except_orm(_('Error at doc write!'), str(e))


@monkeypatch_method(DAVRequestHandler)
def do_MKCOL(self):
    """ create a new collection """

    # according to spec body must be empty
    body = None
    if 'Content-Length' in self.headers:
        l = self.headers['Content-Length']
        if not l == '':
            body = self.rfile.read(atoi(l))

    if body:
        return self.send_status(415)

    dc = self.IFACE_CLASS
    uri = urlparse.urljoin(self.get_baseuri(dc), self.path)
    uri = urllib.unquote(uri)

    try:
        dc.mkcol(uri)
        self.send_status(201)
        self.log_request(201)
    except DAV_Error, (ec, dd):
        self.log_request(ec)
        return self.send_status(ec)


@monkeypatch_method(DAVRequestHandler)
def _HEAD_GET(self, with_body=False):
    """ Returns headers and body for given resource """

    dc = self.IFACE_CLASS
    uri = urlparse.urljoin(self.get_baseuri(dc), self.path)
    uri = urllib.unquote(uri)

    headers = {}

    # get the last modified date (RFC 1123!)
    try:
        headers['Last-Modified'] = dc.get_prop(
            uri, "DAV:", "getlastmodified")
    except DAV_NotFound:
        pass

    # get the ETag if any
    try:
        headers['Etag'] = dc.get_prop(uri, "DAV:", "getetag")
    except DAV_NotFound:
        pass

    headers['Pragma'] = "no-cache"

    # get the content type
    try:
        content_type = dc.get_prop(uri, "DAV:", "getcontenttype")
    except DAV_NotFound:
        content_type = "application/octet-stream"

    range = None
    status_code = 200
    if 'Range' in self.headers:
        p = self.headers['Range'].find("bytes=")
        if p != -1:
            range = self.headers['Range'][p + 6:].split("-")
            status_code = 206

    # get the data
    try:
        data = dc.get_data(uri, range)
    except DAV_Error, (ec, dd):
        self.send_status(ec)
        return ec

    # send the data
    if with_body is False:
        data = None

    if isinstance(data, str) or isinstance(data, unicode):
        self.send_body(data, status_code, None, None, content_type,
                       headers)
    else:
        headers['Keep-Alive'] = 'timeout=15, max=86'
        headers['Connection'] = 'Keep-Alive'
        self.send_body_chunks_if_http11(data, status_code, None, None,
                                        content_type, headers)

    return status_code


BaseHTTPRequestHandler.protocol_version = "HTTP/1.1"

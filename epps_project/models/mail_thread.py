# -*- coding: utf-8 -*-
##############################################################################
# This software is © copyright 2016 EPPS Services Ltd and licensed under the
# GNU Affero General Public License, version 3.0 as published by the Free
# Software Foundation.
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################

import base64
from collections import OrderedDict
import datetime
import dateutil
import email

try:
    import simplejson as json
except ImportError:
    import json
from lxml import etree
import logging
import pytz
import re
import socket
import time
import xmlrpclib
from email.message import Message
from email.utils import formataddr
from urllib import urlencode

from openerp import api, tools
from openerp import SUPERUSER_ID
from openerp.addons.mail.mail_message import decode
from openerp.osv import fields, osv, orm
from openerp.osv.orm import BaseModel
from openerp.tools.safe_eval import safe_eval as eval
from openerp.tools.translate import _
_logger = logging.getLogger(__name__)


class EppsDesignInstalled(orm.AbstractModel):
    '''When you use monkey patching, the code is executed when the module
    is in the addons_path of the OpenERP server, even is the module is not
    installed ! In order to avoid the side-effects it can create,
    we create an AbstractModel inside the module and we test the
    availability of this Model in the code of the monkey patching below.
    At Akretion, we call this the "Guewen trick", in reference
    to a trick used by Guewen Baconnier in the "connector" module.
    '''
    _name = "epps.design.installed"

# monkey patch to override message_track
'''
 monkey patch used because of multiple abstract module inheritance
 overrides whole message_track to remove bulletins from format_message function
 problem with overriding inner functions
'''
from openerp.addons.mail.mail_thread import mail_thread
message_track_orig = mail_thread.message_track


def message_track(self, cr, uid, ids, tracked_fields, initial_values, context=None):
    if self.pool.get('epps.design.installed'):
        def convert_for_display(value, col_info):
            if not value and col_info['type'] == 'boolean':
                return 'False'
            if not value:
                return ''
            if col_info['type'] == 'many2one':
                return value.name_get()[0][1]
            if col_info['type'] == 'selection':
                return dict(col_info['selection'])[value]
            return value

        def format_message(message_description, tracked_values):
            message = ''
            if message_description:
                message = '<span>%s</span>' % message_description
            for name, change in tracked_values.items():
                message += '<div> &nbsp; &nbsp; &nbsp; <b>%s</b>: ' % change.get(
                    'col_info')
                if change.get('old_value'):
                    message += '%s &rarr; ' % change.get('old_value')
                message += '%s</div>' % change.get('new_value')
            return message

        if not tracked_fields:
            return True

        for browse_record in self.browse(cr, uid, ids, context=context):
            initial = initial_values[browse_record.id]
            changes = set()
            tracked_values = {}

            # generate tracked_values data structure: {'col_name': {col_info,
            # new_value, old_value}}
            for col_name, col_info in tracked_fields.items():
                field = self._fields[col_name]
                initial_value = initial[col_name]
                record_value = getattr(browse_record, col_name)

                if record_value == initial_value and getattr(field, 'track_visibility', None) == 'always':
                    tracked_values[col_name] = dict(
                        col_info=col_info['string'],
                        new_value=convert_for_display(record_value, col_info),
                    )
                # because browse null != False
                elif record_value != initial_value and (record_value or initial_value):
                    if getattr(field, 'track_visibility', None) in ['always', 'onchange']:
                        tracked_values[col_name] = dict(
                            col_info=col_info['string'],
                            old_value=convert_for_display(
                                initial_value, col_info),
                            new_value=convert_for_display(
                                record_value, col_info),
                        )
                    if col_name in tracked_fields:
                        changes.add(col_name)
            if not changes:
                continue

            # find subtypes and post messages or log if no subtype found
            subtypes = []
            # By passing this key, that allows to let the subtype empty and so
            # don't sent email because partners_to_notify from
            # mail_message._notify will be empty
            if not context.get('mail_track_log_only'):
                for field, track_info in self._track.items():
                    if field not in changes:
                        continue
                    for subtype, method in track_info.items():
                        if method(self, cr, uid, browse_record, context):
                            subtypes.append(subtype)

            posted = False
            for subtype in subtypes:
                subtype_rec = self.pool.get('ir.model.data').xmlid_to_object(
                    cr, uid, subtype, context=context)

                message = ''

                if not (subtype_rec and subtype_rec.exists()):
                    _logger.debug('subtype %s not found' % subtype)
                    continue
                if subtype == 'document.mt_document_assigned':
                    next_reviewer = ''
                    if tracked_values.get('document_next_reviewer_id', False):
                        next_reviewer = tracked_values['document_next_reviewer_id'].get('new_value', '')
                    document_name = browse_record.name or ''
                    current_user = self.pool('res.users').browse(cr, uid, [uid]).name or ''
                    project_obj = self.pool('project.project').browse(cr, uid, browse_record.res_id)
                    project_name = ''
                    if project_obj:
                        project_name = project_obj[0].name
                    if context.get('file_url', False):
                        document_name = '<a class="notification_file_link" href="%s">%s</a>' %(str(context['file_url']), str(browse_record.name))
                    message = '<div>'
                    message = message + 'Hello %s, <br>Just to let you know that %s has asked' \
                                        ' you to handle the document <b>%s</b> in project <b>%s</b>.' \
                                        %(str(next_reviewer), str(current_user), str(document_name), str(project_name))
                    message = message + '</div>'
                elif subtype == 'document.mt_document_approved':
                    document_approver = ''
                    if browse_record.document_approver_id:
                        document_approver = browse_record.document_approver_id.name or ''
                    document_name = browse_record.name or ''
                    project_obj = self.pool('project.project').browse(cr, uid, browse_record.res_id)
                    project_name = ''
                    if project_obj:
                        project_name = project_obj[0].name
                    if context.get('file_url', False):
                        document_name = '<a class="notification_file_link" href="%s">%s</a>' %(str(context['file_url']), str(browse_record.name))
                    message = '<div>'
                    message = message + 'Hello, <br>Just to let you know that %s has approved' \
                                        ' the document <b>%s</b> in project <b>%s</b>.' \
                                        %(str(document_approver), str(document_name), str(project_name))
                    message = message + '</div>'
                else:
                    message = format_message(
                        subtype_rec.description if subtype_rec.description else subtype_rec.name, tracked_values)
                self.message_post(cr, uid, browse_record.id,
                                  body=message, subtype=subtype, context=context)
                posted = True
            if not posted:
                message = format_message('', tracked_values)
                self.message_post(cr, uid, browse_record.id,
                                  body=message, context=context)
        res = True
    else:
        res = message_track_orig(
            self, cr, uid, ids, tracked_fields, initial_values, context=context)
    return res

mail_thread.message_track = message_track
# end of monkey patch

# monkey patch to override _get_access_link
_get_access_link_orig = mail_thread._get_access_link


def _get_access_link(self, cr, uid, mail, partner, context=None):
    if self.pool.get('epps.design.installed'):
        query = {'db': cr.dbname}
        fragment = {
            'login': partner.user_ids[0].login,
            'action': 'mail.action_mail_redirect',
        }
        if mail.notification:
            fragment['message_id'] = mail.mail_message_id.id
        elif mail.model and mail.res_id:
            fragment.update(model=mail.model, res_id=mail.res_id)

        res = "/web?%s#%s" % (urlencode(query), urlencode(fragment))
        #res = "TU ZAMJENI LINK"
    else:
        res = _get_access_link_orig(
            self, cr, uid, mail, partner, context=context)
    return res

mail_thread._get_access_link = _get_access_link
# end of monkey patch


class MailThread(osv.AbstractModel):
    _name = 'mail.thread'
    _inherit = ['mail.thread']

    @api.cr_uid_ids_context
    def message_post(self, cr, uid, thread_id, body='', subject=None, type='notification',
                     subtype=None, parent_id=False, attachments=None, context=None,
                     content_subtype='html', **kwargs):
        """ Post a new message in an existing thread, returning the new
            mail.message ID.

            :param int thread_id: thread ID to post into, or list with one ID;
                if False/0, mail.message model will also be set as False
            :param str body: body of the message, usually raw HTML that will
                be sanitized
            :param str type: see mail_message.type field
            :param str content_subtype:: if plaintext: convert body into html
            :param int parent_id: handle reply to a previous message by adding the
                parent partners to the message in case of private discussion
            :param tuple(str,str) attachments or list id: list of attachment tuples in the form
                ``(name,content)``, where content is NOT base64 encoded

            Extra keyword arguments will be used as default column values for the
            new mail.message record. Special cases:
                - attachment_ids: supposed not attached to any document; attach them
                    to the related document. Should only be set by Chatter.
            :return int: ID of newly created mail.message
        """

        _logger.info("message_post")

        if context is None:
            context = {}
        if attachments is None:
            attachments = {}
        mail_message = self.pool.get('mail.message')
        ir_attachment = self.pool.get('ir.attachment')
        message_tags = self.pool.get('message.tags')

        assert (not thread_id) or \
            isinstance(thread_id, (int, long)) or \
               (isinstance(thread_id, (list, tuple)) and len(thread_id) == 1), \
            "Invalid thread_id; should be 0, False, an ID or a list with one ID"
        if isinstance(thread_id, (list, tuple)):
            thread_id = thread_id[0]

        # if we're processing a message directly coming from the gateway, the destination model was
        # set in the context.
        model = False
        if thread_id:
            model = context.get(
                'thread_model', False) if self._name == 'mail.thread' else self._name
            if model and model != self._name and hasattr(self.pool[model], 'message_post'):
                del context['thread_model']
                return self.pool[model].message_post(cr, uid, thread_id, body=body, subject=subject, type=type,
                                                     subtype=subtype, parent_id=parent_id, attachments=attachments,
                                                     context=context, content_subtype=content_subtype, **kwargs)

        # 0: Find the message's author, because we need it for private
        # discussion
        author_id = kwargs.get('author_id')
        if author_id is None:  # keep False values
            author_id = self.pool.get('mail.message')._get_default_author(
                cr, uid, context=context)

        # 1: Handle content subtype: if plaintext, converto into HTML
        if content_subtype == 'plaintext':
            body = tools.plaintext2html(body)

        # 2: Private message: add recipients (recipients and author of parent message) - current author
        #   + legacy-code management (! we manage only 4 and 6 commands)
        partner_ids = set()
        kwargs_partner_ids = kwargs.pop('partner_ids', [])
        for partner_id in kwargs_partner_ids:
            if isinstance(partner_id, (list, tuple)) and partner_id[0] == 4 and len(partner_id) == 2:
                partner_ids.add(partner_id[1])
            if isinstance(partner_id, (list, tuple)) and partner_id[0] == 6 and len(partner_id) == 3:
                partner_ids |= set(partner_id[2])
            elif isinstance(partner_id, (int, long)):
                partner_ids.add(partner_id)
            else:
                pass  # we do not manage anything else
        if parent_id and not model:
            parent_message = mail_message.browse(
                cr, uid, parent_id, context=context)
            private_followers = set(
                [partner.id for partner in parent_message.partner_ids])
            if parent_message.author_id:
                private_followers.add(parent_message.author_id.id)
            private_followers -= set([author_id])
            partner_ids |= private_followers

        # 3. Attachments
        #   - HACK TDE FIXME: Chatter: attachments linked to the document (not done JS-side), load the message
        attachment_ids = self._message_preprocess_attachments(cr, uid, attachments, kwargs.pop('attachment_ids', []),
                                                              model, thread_id, context)

        # 4: mail.message.subtype
        subtype_id = False
        if subtype:
            if '.' not in subtype:
                subtype = 'mail.%s' % subtype
            subtype_id = self.pool.get(
                'ir.model.data').xmlid_to_res_id(cr, uid, subtype)

        # automatically subscribe recipients if asked to
        if context.get('mail_post_autofollow') and thread_id and partner_ids:
            partner_to_subscribe = partner_ids
            if context.get('mail_post_autofollow_partner_ids'):
                partner_to_subscribe = filter(lambda item: item in context.get('mail_post_autofollow_partner_ids'),
                                              partner_ids)
            self.message_subscribe(cr, uid, [thread_id], list(
                partner_to_subscribe), context=context)

        # _mail_flat_thread: automatically set free messages to the first
        # posted message
        if self._mail_flat_thread and model and not parent_id and thread_id:
            message_ids = mail_message.search(cr, uid, ['&', ('res_id', '=', thread_id), ('model', '=', model),
                                                        ('type', '=', 'email')], context=context, order="id ASC",
                                              limit=1)
            if not message_ids:
                message_ids = message_ids = mail_message.search(cr, uid, ['&', ('res_id', '=', thread_id),
                                                                          ('model', '=', model)], context=context,
                                                                order="id ASC", limit=1)
            parent_id = message_ids and message_ids[0] or False
        # we want to set a parent: force to set the parent_id to the oldest
        # ancestor, to avoid having more than 1 level of thread
        elif parent_id:
            message_ids = mail_message.search(cr, SUPERUSER_ID, [('id', '=', parent_id), ('parent_id', '!=', False)],
                                              context=context)
            # avoid loops when finding ancestors
            processed_list = []
            if message_ids:
                message = mail_message.browse(
                    cr, SUPERUSER_ID, message_ids[0], context=context)
                while (message.parent_id and message.parent_id.id not in processed_list):
                    processed_list.append(message.parent_id.id)
                    message = message.parent_id
                parent_id = message.id

        values = kwargs
        values.update({
            'author_id': author_id,
            'model': model,
            'res_id': model and thread_id or False,
            'body': body,
            'subject': subject or False,
            'type': type,
            'parent_id': parent_id,
            'attachment_ids': attachment_ids,
            'message_tags_ids': [],
            'subtype_id': subtype_id,
            'partner_ids': [(4, pid) for pid in partner_ids],
        })

        # Avoid warnings about non-existing fields
        for x in ('from', 'to', 'cc'):
            values.pop(x, None)

        # Post the message
        msg_id = mail_message.create(cr, uid, values, context=context)

        # Post-process: subscribe author, update message_last_post
        if model and model != 'mail.thread' and thread_id and subtype_id:
            # done with SUPERUSER_ID, because on some models users can post
            # only with read access, not necessarily write access
            self.write(cr, SUPERUSER_ID, [thread_id], {
                       'message_last_post': fields.datetime.now()}, context=context)
        message = mail_message.browse(cr, uid, msg_id, context=context)
        if message.author_id and model and thread_id and type != 'notification' and not context.get(
                'mail_create_nosubscribe'):
            self.message_subscribe(cr, uid, [thread_id], [
                                   message.author_id.id], context=context)
        return msg_id

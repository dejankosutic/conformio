# -*- coding: utf-8 -*-
##############################################################################
# This software is © copyright 2016 EPPS Services Ltd and licensed under the
# GNU Affero General Public License, version 3.0 as published by the Free
# Software Foundation.
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################

import logging
import re
from openerp import tools

from email.header import decode_header
from email.utils import formataddr
from openerp import SUPERUSER_ID, api
from openerp.osv import osv, orm, fields
from openerp.tools import html_email_clean
from openerp.tools import html2plaintext
from openerp.tools.translate import _
from HTMLParser import HTMLParser
from openerp.osv.orm import BaseModel

# _logger = logging.getLogger(__name__)message_tags_save
_logger = logging.getLogger('eee')


class MailMessage(osv.Model):
    _name = 'mail.message'
    _inherit = ['mail.message']

    def _search_followers(self, cr, uid, obj, name, args, context):
        """Search function for message_follower_ids

        Do not use with operator 'not in'. Use instead message_is_followers
        """
        fol_obj = self.pool.get('mail.followers')
        res = []
        for field, operator, value in args:
            assert field == name
            # TOFIX make it work with not in
            assert operator != "not in", "Do not search message_follower_ids with 'not in'"
            fol_ids = fol_obj.search(cr, SUPERUSER_ID,
                                     [('res_model', '=', self._name), ('partner_id', operator, value)])
            res_ids = [fol.res_id for fol in fol_obj.browse(
                cr, SUPERUSER_ID, fol_ids)]
            res.append(('id', 'in', res_ids))
        return res

    def _search_is_follower(self, cr, uid, obj, name, args, context):
        """Search function for message_is_follower"""
        res = []
        for field, operator, value in args:
            assert field == name
            partner_id = self.pool.get('res.users').browse(
                cr, uid, uid, context=context).partner_id.id
            if (operator == '=' and value) or (operator == '!=' and not value):  # is a follower
                res_ids = self.search(
                    cr, uid, [('message_follower_ids', 'in', [partner_id])], context=context)
            else:  # is not a follower or unknown domain
                mail_ids = self.search(
                    cr, uid, [('message_follower_ids', 'in', [partner_id])], context=context)
                res_ids = self.search(
                    cr, uid, [('id', 'not in', mail_ids)], context=context)
            res.append(('id', 'in', res_ids))
        return res

    def extractHash(self, cr, uid, str, context=None):
        tags = re.findall(r"#(\w+)", str)
        message_tags = self.pool['message.tags']
        m2m_attachment_ids = []
        if tags:
            for name in tags:
                nid = message_tags.create(
                    cr, uid, {'tag': name.replace("#", ""), }, context=context)
                m2m_attachment_ids.append(nid)
        return m2m_attachment_ids

    def message_tags_save(self, cr, uid, ids, context=None):
        return True

    def unlink(self, cr, uid, ids, context=None):
        #We need to execute this with superuser id since message res_id is sometimes 0 or false
        return super(MailMessage, self).unlink(cr, SUPERUSER_ID, ids, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        #We need to execute this with superuser id since message res_id is sometimes 0 or false
        if not vals:
            vals = {}
        partner_obj = self.pool['res.users'].browse(cr, SUPERUSER_ID, uid, context=context)
        message_obj = self.pool('mail.message').browse(cr, uid, ids, context=context)
        if message_obj and partner_obj and vals.get('message_tags_ids', False):
            for msg in message_obj:
                if msg.author_id.id != partner_obj.partner_id.id:
                    return super(MailMessage, self).write(cr, SUPERUSER_ID, ids, vals, context=context)
        return super(MailMessage, self).write(cr, uid, ids, vals, context=context)

    def create(self, cr, uid, values, context=None):
        context = dict(context or {})
        default_starred = context.pop('default_starred', False)
        if 'email_from' not in values:  # needed to compute reply_to
            values['email_from'] = self._get_default_from(
                cr, uid, context=context)
        if not values.get('message_id'):
            values['message_id'] = self._get_message_id(
                cr, uid, values, context=context)
        if 'reply_to' not in values:
            values['reply_to'] = self._get_reply_to(
                cr, uid, values, context=context)
        if 'record_name' not in values and 'default_record_name' not in context:
            values['record_name'] = self._get_record_name(
                cr, uid, values, context=context)

        # attach tags to message
        if 'message_tags_ids' in values:
            vals = values.get('message_tags_ids', list())
            message_tags_ids = []
            for v in vals:
                message_tags_ids.append([4, v])
            values['message_tags_ids'] = message_tags_ids
        else:
            vals = self.extractHash(cr, uid, values.get('body'), context)
            message_tags_ids = []
            for v in vals:
                message_tags_ids.append([4, v])
            values['message_tags_ids'] = message_tags_ids

        # message_tags_ids = values.get('message_tags_ids') or []
        #message_tags_ids.append([4, 436432])
        #values['message_tags_ids'] = message_tags_ids

        newid = super(MailMessage, self).create(cr, uid, values, context)

        #self.message_tags_ids = [436432,]

        self._notify(cr, uid, newid, context=context,
                     force_send=context.get('mail_notify_force_send', True),
                     user_signature=context.get('mail_notify_user_signature', True))
        # TDE FIXME: handle default_starred. Why not setting an inv on starred ?
        # Because starred will call set_message_starred, that looks for notifications.
        # When creating a new mail_message, it will create a notification to a message
        # that does not exist, leading to an error (key not existing). Also this
        # this means unread notifications will be created, yet we can not assure
        # this is what we want.
        if default_starred:
            self.set_message_starred(cr, uid, [newid], True, context=context)
        return newid

    def _get_followers(self, cr, uid, ids, name, arg, context=None):
        fol_obj = self.pool.get('mail.followers')
        fol_ids = fol_obj.search(
            cr, SUPERUSER_ID, [('res_model', '=', self._name), ('res_id', 'in', ids)])
        res = dict((id, dict(message_follower_ids=[],
                             message_is_follower=False)) for id in ids)
        user_pid = self.pool.get('res.users').read(
            cr, uid, [uid], ['partner_id'], context=context)[0]['partner_id'][0]
        for fol in fol_obj.browse(cr, SUPERUSER_ID, fol_ids):
            res[fol.res_id]['message_follower_ids'].append(fol.partner_id.id)
            if fol.partner_id.id == user_pid:
                res[fol.res_id]['message_is_follower'] = True
        return res

    def _set_followers(self, cr, uid, id, name, value, arg, context=None):
        if not value:
            return
        partner_obj = self.pool.get('res.partner')
        fol_obj = self.pool.get('mail.followers')

        # read the old set of followers, and determine the new set of followers
        fol_ids = fol_obj.search(
            cr, SUPERUSER_ID, [('res_model', '=', self._name), ('res_id', '=', id)])
        old = set(fol.partner_id.id for fol in fol_obj.browse(
            cr, SUPERUSER_ID, fol_ids))
        new = set(old)

        for command in value or []:
            if isinstance(command, (int, long)):
                new.add(command)
            elif command[0] == 0:
                new.add(partner_obj.create(
                    cr, uid, command[2], context=context))
            elif command[0] == 1:
                partner_obj.write(cr, uid, [command[1]], command[
                                  2], context=context)
                new.add(command[1])
            elif command[0] == 2:
                partner_obj.unlink(cr, uid, [command[1]], context=context)
                new.discard(command[1])
            elif command[0] == 3:
                new.discard(command[1])
            elif command[0] == 4:
                new.add(command[1])
            elif command[0] == 5:
                new.clear()
            elif command[0] == 6:
                new = set(command[2])

        # remove partners that are no longer followers
        self.message_unsubscribe(
            cr, uid, [id], list(old - new), context=context)
        # add new followers
        self.message_subscribe(cr, uid, [id], list(new - old), context=context)

    _columns = {
        'message_is_follower': fields.function(_get_followers, type='boolean',
                                               fnct_search=_search_is_follower, string='Is a Follower',
                                               multi='_get_followers,'),
        'message_tags_ids': fields.many2many('message.tags', 'mail_message_message_tags_rel', 'message_id', 'tag_id',
                                             'Tags'),
        'message_follower_ids': fields.function(_get_followers, fnct_inv=_set_followers,
                                                fnct_search=_search_followers, type='many2many', priority=-10,
                                                obj='res.partner', string='Followers', multi='_get_followers'),

    }
    _message_read_fields = ['id', 'parent_id', 'model', 'res_id', 'body', 'subject', 'date', 'to_read', 'email_from',
                            'type', 'vote_user_ids', 'attachment_ids', 'author_id', 'partner_ids', 'record_name',
                            'message_tags_ids']

    def email_me(self, cr, uid, messageID, context=None):
        """
        Send mail_message object as email.

        :param cr:
        :param uid:
        :param messageID: mail_message ID
        :param context:
        :return:
        """
        if not context:
            context = {}
        
        # get current message
        message = self.browse(cr, SUPERUSER_ID, messageID, context=context)
        context.update({'email_me': True,
                        'model': message.model,
                        'res_id': message.res_id})
        # get user email based on user ID
        pemail = self.pool['res.users'].browse(
            cr, SUPERUSER_ID, uid, context=context).partner_id.email

        mail_mail = self.pool.get('mail.mail')
        child_messages = message.child_ids
        message_author = ""
        if message.author_id:
            message_author = message.author_id.name
        record_name = _("My Discussion")
        if message.res_id != 0:
            record_name = message.record_name
        whole_body ="<table><tr><td><span style = 'font-weight: bold;'>" + _("On") + " " + str(record_name) \
                    + "</span>" + " <span style='font-weight:bold;'>" + str(message_author) + "</span> " \
                    + _("wrote:") + str(message.body) + "</td></tr>"
        for child_message in child_messages:
            if child_message.author_id:
                message_author = child_message.author_id.name
            child_body = "<tr><td style='padding-left:20px;'><span style='font-weight:bold;'>"\
                         + str(message_author) + "</span>" + " " + _("wrote:") + str(child_message.body) + "</td></tr>"
            whole_body = whole_body + child_body
        whole_body = whole_body + "</table>"
        subject = html2plaintext(str(whole_body))
        subject = " ".join(subject.split())
        this = self.pool.get('res.users').browse(cr, SUPERUSER_ID, uid, context=context)
        email_from = formataddr((this.name + ' on Conformio', 'do-not-reply@conformio.com'))
        mail_id = mail_mail.create(cr, uid, {
            'body_html': whole_body,
            'subject': str(subject[:30]),
            'email_to': pemail,
            'email_from': email_from,
            'reply_to': '',
            'auto_delete': True,
        }, context=context)

        mail_mail.send(cr, uid, [mail_id], context=context)

    def get_messages_from_tags(self, cr, uid, tag, res_id, context=None):
        message_tags = self.pool['message.tags']
        MailMessage = self.pool['mail.message']
        tag_ids = message_tags.search(cr, uid, [('tag', '=', tag)])
        if len(tag_ids) > 0:
            message_ids = MailMessage.search(
                cr, uid, [['message_tags_ids', 'in', tag_ids], ['res_id', '=', res_id]])
            if len(message_ids) > 0:
                return message_ids
        return []

    def on_like_toggle(self, cr, uid, ids, context=None):
        ''' Toggles vote. Performed using read to avoid access rights issues.
            Done as SUPERUSER_ID because uid may vote for a message he cannot modify. '''
        context = context or {}
        for message in self.read(cr, uid, ids, ['vote_user_ids'], context=context):
            like_count = len(message.get('vote_user_ids'))
            new_has_voted = not (uid in message.get('vote_user_ids'))
            if new_has_voted:
                user_obj = self.pool.get('res.users')
                # update context with user so we can access it's name on mail template
                context.update({'user_liked': user_obj.browse(cr, SUPERUSER_ID, [uid], context=context)})
                self.write(cr, SUPERUSER_ID, message.get('id'), {
                           'vote_user_ids': [(4, uid)]}, context=context)
                like_count += 1
                try:
                    # check if user wants to recive email for message like
                    check_user_settings = self.check_user_settings(cr, SUPERUSER_ID, message.get('id'), context=context)
                    if check_user_settings:
                        self.send_mail(cr, SUPERUSER_ID, message.get('id'), context=context)
                except Exception:
                    pass
            else:
                self.write(cr, SUPERUSER_ID, message.get('id'), {
                           'vote_user_ids': [(3, uid)]}, context=context)
                like_count -= 1
            return like_count

    def check_user_settings(self, cr, uid, id, context=None):
        #check if user wants to recive an email or not
        #return True  # uncomment for testing
        messages = self.browse(cr, uid, [id], context=context)
        for message in messages:
            if message.create_uid.message_like:
                return True
            else:
                return False

    def send_mail(self, cr, uid, id, context=None):
        # find template 'email_temp_message_liked' (defined in xml) and send mail
        ir_model_data = self.pool.get('ir.model.data')
        template_pool = self.pool.get('email.template')
        template_id = False
        model, template_id = ir_model_data.get_object_reference(cr, uid, 'epps_project', 'email_temp_message_liked')
        template_pool.send_mail(cr, SUPERUSER_ID, template_id, id, force_send=True, raise_exception=False, context=context)
        return True

    def send_access_request_mail(self, cr, uid, message_id, context=None):
        """Sends the access request mail from request message."""
        message_obj = self.pool.get('mail.message').browse(cr, SUPERUSER_ID, message_id, context=context)
        current_user = self.pool.get('res.users').browse(cr, SUPERUSER_ID, uid, context=context)
        email_from = formataddr((current_user.name + ' on Conformio', 'do-not-reply@conformio.com'))
        mail_mail = self.pool('mail.mail')

        if message_obj:
            if message_obj.partner_ids:
                target_user = message_obj.partner_ids.user_ids
                user_settings = {'notifications': {'message_received': target_user.message_received or False,
                                                   'tasks_change': target_user.tasks_change or False,
                                                   'documents_change': target_user.documents_change or False,
                                                   'new_login': target_user.user_ids.new_login or False,
                                                   'project_invite': target_user.project_invite or False,
                                                   'message_like': target_user.message_like or False,
                                                   'important_updates': target_user.important_updates or False,
                                                   },
                                 'projects': [project.id for project in target_user.projects_to_follow]}
                if user_settings['notifications']['message_received']:
                    subject = message_obj.subject or ''
                    whole_body = message_obj.body or ''
                    pemail = message_obj.partner_ids.email or ''
                    mail_id = mail_mail.create(cr, uid, {
                        'body_html': whole_body,
                        'subject': str(subject[:30]),
                        'email_to': pemail,
                        'email_from': email_from,
                        'reply_to': '',
                        'auto_delete': True,
                    }, context=context)
                    return mail_mail.send(cr, uid, [mail_id], context=context)
        return False

    def on_get_like_count(self, cr, uid, ids, context=None):
        for message in self.read(cr, uid, ids, ['vote_user_ids'], context=context):
            like_count = len(message.get('vote_user_ids'))
            return like_count

    def _message_read_dict_postprocess(self, cr, uid, messages, message_tree, context=None):
        """ Post-processing on values given by message_read. This method will
            handle partners in batch to avoid doing numerous queries.

            :param list messages: list of message, as get_dict result
            :param dict message_tree: {[msg.id]: msg browse record}
        """
        res_partner_obj = self.pool.get('res.partner')
        ir_attachment_obj = self.pool.get('ir.attachment')
        message_tags_obj = self.pool.get('message.tags')
        pid = self.pool['res.users'].browse(
            cr, SUPERUSER_ID, uid, context=context).partner_id.id

        # 1. Aggregate partners (author_id and partner_ids) and attachments
        partner_ids = set()
        attachment_ids = set()
        message_tags_ids = set()
        for key, message in message_tree.iteritems():
            if message.author_id:
                partner_ids |= set([message.author_id.id])
            if message.subtype_id and message.notified_partner_ids:  # take notified people of message with a subtype
                partner_ids |= set(
                    [partner.id for partner in message.notified_partner_ids])
            # take specified people of message without a subtype (log)
            elif not message.subtype_id and message.partner_ids:
                partner_ids |= set(
                    [partner.id for partner in message.partner_ids])
            if message.attachment_ids:
                attachment_ids |= set(
                    [attachment.id for attachment in message.attachment_ids])
            if message.message_tags_ids:
                message_tags_ids |= set(
                    [message_tags.id for message_tags in message.message_tags_ids])
        # Read partners as SUPERUSER -> display the names like classic m2o even
        # if no access
        partners = res_partner_obj.name_get(
            cr, SUPERUSER_ID, list(partner_ids), context=context)
        partner_tree = dict((partner[0], partner) for partner in partners)

        # 2. Attachments as SUPERUSER, because could receive msg and
        # attachments for doc uid cannot see
        attachments = ir_attachment_obj.read(cr, SUPERUSER_ID, list(attachment_ids),
                                             ['id', 'datas_fname', 'name', 'file_type_icon'], context=context)
        attachments_tree = dict((attachment['id'], {
            'id': attachment['id'],
            'filename': attachment['datas_fname'],
            'name': attachment['name'],
            'file_type_icon': attachment['file_type_icon'],
        }) for attachment in attachments)

        message_tags = message_tags_obj.read(cr, SUPERUSER_ID, list(
            message_tags_ids), ['id', 'tag'], context=context)
        message_tags_tree = dict((message_tag['id'], {
            'id': message_tag['id'],
            'tag': message_tag['tag'],
        }) for message_tag in message_tags)

        # 3. Update message dictionaries
        for message_dict in messages:
            message_id = message_dict.get('id')
            message = message_tree[message_id]
            if message.author_id:
                author = partner_tree[message.author_id.id]
            else:
                author = (0, message.email_from)
            partner_ids = []
            if message.subtype_id:
                partner_ids = [partner_tree[partner.id] for partner in message.notified_partner_ids
                               if partner.id in partner_tree]
            else:
                partner_ids = [partner_tree[partner.id] for partner in message.partner_ids
                               if partner.id in partner_tree]
            attachment_ids = []
            for attachment in message.attachment_ids:
                if attachment.id in attachments_tree:
                    attachment_ids.append(attachments_tree[attachment.id])

            message_tags_ids = []
            for message_tag in message.message_tags_ids:
                if message_tag.id in message_tags_tree:
                    message_tags_ids.append(message_tags_tree[message_tag.id])

            # _logger.info("message_tags_ids %s", message_tags_ids)
            # _logger.info("partner_ids %s", partner_ids)
            # _logger.info("message.message_tags_ids %s", message.message_tags_ids)

            message_dict.update({
                'is_author': pid == author[0],
                'author_id': author,
                'partner_ids': partner_ids,
                'attachment_ids': attachment_ids,
                'message_tags_ids': message_tags_ids,
                'user_pid': pid
            })
        return True

    def _message_read_dict(self, cr, uid, message, parent_id=False, context=None):
        """ Return a dict representation of the message. This representation is
            used in the JS client code, to display the messages. Partners and
            attachments related stuff will be done in post-processing in batch.

            :param dict message: mail.message browse record
        """
        # private message: no model, no res_id
        is_private = False
        if not message.model or not message.res_id:
            is_private = True
        # votes and favorites: res.users ids, no prefetching should be done
        vote_nb = len(message.vote_user_ids)
        has_voted = uid in [user.id for user in message.vote_user_ids]

        try:
            if parent_id:
                max_length = 300
            else:
                max_length = 100
            body_short = html_email_clean(
                message.body, remove=False, shorten=True, max_length=max_length)

        except Exception:
            body_short = '<p><b>Encoding Error : </b><br/>Unable to convert this message (id: %s).</p>' % message.id
            _logger.exception(Exception)

        return {'id': message.id,
                'type': message.type,
                'subtype': message.subtype_id.name if message.subtype_id else False,
                'body': message.body,
                'body_short': body_short,
                'model': message.model,
                'res_id': message.res_id,
                'record_name': message.record_name,
                'subject': message.subject,
                'date': message.date,
                'to_read': message.to_read,
                'parent_id': parent_id,
                'is_private': is_private,
                'author_id': False,
                'author_avatar': message.author_avatar,
                'is_author': False,
                'partner_ids': [],
                'vote_nb': vote_nb,
                'message_is_follower': message.message_is_follower,
                'message_tags_ids': [],
                'has_voted': has_voted,
                'is_favorite': message.starred,
                'attachment_ids': [],
                }

    def message_get_subscription_data(self, cr, uid, ids, user_pid=None, context=None):
        """ Wrapper to get subtypes data. """
        return self._get_subscription_data(cr, uid, ids, None, None, user_pid=user_pid, context=context)

    def message_subscribe_users(self, cr, uid, ids, user_ids=None, subtype_ids=None, context=None):
        """ Wrapper on message_subscribe, using users. If user_ids is not
            provided, subscribe uid instead. """
        if user_ids is None:
            user_ids = [uid]
        partner_ids = [user.partner_id.id for user in
                       self.pool.get('res.users').browse(cr, uid, user_ids, context=context)]
        result = self.message_subscribe(
            cr, uid, ids, partner_ids, subtype_ids=subtype_ids, context=context)
        if partner_ids and result:
            self.pool['ir.ui.menu'].clear_cache()
        return result

    def message_subscribe(self, cr, uid, ids, partner_ids, subtype_ids=None, context=None):
        """ Add partners to the records followers. """
        if context is None:
            context = {}
        # not necessary for computation, but saves an access right check
        if not partner_ids:
            return True

        mail_followers_obj = self.pool.get('mail.followers')
        subtype_obj = self.pool.get('mail.message.subtype')

        user_pid = self.pool.get('res.users').browse(
            cr, uid, uid, context=context).partner_id.id
        if set(partner_ids) == set([user_pid]):
            try:
                self.check_access_rights(cr, uid, 'read')
                self.check_access_rule(cr, uid, ids, 'read')
            except (osv.except_osv, orm.except_orm):
                return False
        else:
            self.check_access_rights(cr, uid, 'write')
            self.check_access_rule(cr, uid, ids, 'write')

        existing_pids_dict = {}
        fol_ids = mail_followers_obj.search(cr, SUPERUSER_ID,
                                            ['&', '&', ('res_model', '=', self._name), ('res_id', 'in', ids),
                                             ('partner_id', 'in', partner_ids)])
        for fol in mail_followers_obj.browse(cr, SUPERUSER_ID, fol_ids, context=context):
            existing_pids_dict.setdefault(
                fol.res_id, set()).add(fol.partner_id.id)

        # subtype_ids specified: update already subscribed partners
        if subtype_ids and fol_ids:
            mail_followers_obj.write(cr, SUPERUSER_ID, fol_ids, {'subtype_ids': [
                                     (6, 0, subtype_ids)]}, context=context)
        # subtype_ids not specified: do not update already subscribed partner,
        # fetch default subtypes for new partners
        if subtype_ids is None:
            subtype_ids = subtype_obj.search(
                cr, uid, [
                    ('default', '=', True), '|', ('res_model', '=', self._name), ('res_model', '=', False)],
                context=context)

        for id in ids:
            existing_pids = existing_pids_dict.get(id, set())
            new_pids = set(partner_ids) - existing_pids

            # subscribe new followers
            for new_pid in new_pids:
                mail_followers_obj.create(
                    cr, SUPERUSER_ID, {
                        'res_model': self._name,
                        'res_id': id,
                        'partner_id': new_pid,
                        'subtype_ids': [(6, 0, subtype_ids)],
                    }, context=context)

        return True

    def message_unsubscribe_users(self, cr, uid, ids, user_ids=None, context=None):
        """ Wrapper on message_subscribe, using users. If user_ids is not
            provided, unsubscribe uid instead. """
        if user_ids is None:
            user_ids = [uid]
        partner_ids = [user.partner_id.id for user in
                       self.pool.get('res.users').browse(cr, uid, user_ids, context=context)]
        result = self.message_unsubscribe(
            cr, uid, ids, partner_ids, context=context)
        if partner_ids and result:
            self.pool['ir.ui.menu'].clear_cache()
        return result

    def message_unsubscribe(self, cr, uid, ids, partner_ids, context=None):
        """ Remove partners from the records followers. """
        # not necessary for computation, but saves an access right check
        if not partner_ids:
            return True
        user_pid = self.pool.get('res.users').read(
            cr, uid, uid, ['partner_id'], context=context)['partner_id'][0]
        if set(partner_ids) == set([user_pid]):
            self.check_access_rights(cr, uid, 'read')
            self.check_access_rule(cr, uid, ids, 'read')
        else:
            self.check_access_rights(cr, uid, 'write')
            self.check_access_rule(cr, uid, ids, 'write')
        fol_obj = self.pool['mail.followers']
        fol_ids = fol_obj.search(
            cr, SUPERUSER_ID, [
                ('res_model', '=', self._name),
                ('res_id', 'in', ids),
                ('partner_id', 'in', partner_ids)
            ], context=context)
        return fol_obj.unlink(cr, SUPERUSER_ID, fol_ids, context=context)

    def _message_get_auto_subscribe_fields(self, cr, uid, updated_fields, auto_follow_fields=None, context=None):
        """ Returns the list of relational fields linking to res.users that should
            trigger an auto subscribe. The default list checks for the fields
            - called 'user_id'
            - linking to res.users
            - with track_visibility set
            In OpenERP V7, this is sufficent for all major addon such as opportunity,
            project, issue, recruitment, sale.
            Override this method if a custom behavior is needed about fields
            that automatically subscribe users.
        """
        if auto_follow_fields is None:
            auto_follow_fields = ['user_id']
        user_field_lst = []
        for name, field in self._fields.items():
            if name in auto_follow_fields and name in updated_fields and getattr(field, 'track_visibility',
                                                                                 False) and field.comodel_name == 'res.users':
                user_field_lst.append(name)
        return user_field_lst

    def _message_auto_subscribe_notify(self, cr, uid, ids, partner_ids, context=None):
        """ Send notifications to the partners automatically subscribed to the thread
            Override this method if a custom behavior is needed about partners
            that should be notified or messages that should be sent
        """
        # find first email message, set it as unread for auto_subscribe fields
        # for them to have a notification
        if partner_ids:
            for record_id in ids:
                message_obj = self.pool.get('mail.message')
                msg_ids = message_obj.search(cr, SUPERUSER_ID, [
                    ('model', '=', self._name),
                    ('res_id', '=', record_id),
                    ('type', '=', 'email')], limit=1, context=context)
                if not msg_ids:
                    msg_ids = message_obj.search(cr, SUPERUSER_ID, [
                        ('model', '=', self._name),
                        ('res_id', '=', record_id)], limit=1, context=context)
                if msg_ids:
                    notification_obj = self.pool.get('mail.notification')
                    notification_obj._notify(
                        cr, uid, msg_ids[0], partners_to_notify=partner_ids, context=context)
                    message = message_obj.browse(
                        cr, uid, msg_ids[0], context=context)
                    if message.parent_id:
                        partner_ids_to_parent_notify = set(partner_ids).difference(
                            partner.id for partner in message.parent_id.notified_partner_ids)
                        for partner_id in partner_ids_to_parent_notify:
                            notification_obj.create(cr, uid, {
                                'message_id': message.parent_id.id,
                                'partner_id': partner_id,
                                'is_read': True,
                            }, context=context)

    def message_auto_subscribe(self, cr, uid, ids, updated_fields, context=None, values=None):
        """ Handle auto subscription. Two methods for auto subscription exist:

         - tracked res.users relational fields, such as user_id fields. Those fields
           must be relation fields toward a res.users record, and must have the
           track_visilibity attribute set.
         - using subtypes parent relationship: check if the current model being
           modified has an header record (such as a project for tasks) whose followers
           can be added as followers of the current records. Example of structure
           with project and task:

          - st_project_1.parent_id = st_task_1
          - st_project_1.res_model = 'project.project'
          - st_project_1.relation_field = 'project_id'
          - st_task_1.model = 'project.task'

        :param list updated_fields: list of updated fields to track
        :param dict values: updated values; if None, the first record will be browsed
                            to get the values. Added after releasing 7.0, therefore
                            not merged with updated_fields argumment.
        """
        subtype_obj = self.pool.get('mail.message.subtype')
        follower_obj = self.pool.get('mail.followers')
        new_followers = dict()

        # fetch auto_follow_fields: res.users relation fields whose changes are
        # tracked for subscription
        user_field_lst = self._message_get_auto_subscribe_fields(
            cr, uid, updated_fields, context=context)

        # fetch header subtypes
        header_subtype_ids = subtype_obj.search(cr, uid, ['|', ('res_model', '=', False),
                                                          ('parent_id.res_model', '=', self._name)], context=context)
        subtypes = subtype_obj.browse(
            cr, uid, header_subtype_ids, context=context)

        # if no change in tracked field or no change in tracked relational
        # field: quit
        relation_fields = set(
            [subtype.relation_field for subtype in subtypes if subtype.relation_field is not False])
        if not any(relation in updated_fields for relation in relation_fields) and not user_field_lst:
            return True

        # legacy behavior: if values is not given, compute the values by browsing
        # @TDENOTE: remove me in 8.0
        if values is None:
            record = self.browse(cr, uid, ids[0], context=context)
            for updated_field in updated_fields:
                field_value = getattr(record, updated_field)
                if isinstance(field_value, BaseModel):
                    field_value = field_value.id
                values[updated_field] = field_value

        # find followers of headers, update structure for new followers
        headers = set()
        for subtype in subtypes:
            if subtype.relation_field and values.get(subtype.relation_field):
                headers.add(
                    (subtype.res_model, values.get(subtype.relation_field)))
        if headers:
            header_domain = ['|'] * (len(headers) - 1)
            for header in headers:
                header_domain += ['&', ('res_model', '=',
                                        header[0]), ('res_id', '=', header[1])]
            header_follower_ids = follower_obj.search(
                cr, SUPERUSER_ID,
                header_domain,
                context=context
            )
            for header_follower in follower_obj.browse(cr, SUPERUSER_ID, header_follower_ids, context=context):
                for subtype in header_follower.subtype_ids:
                    if subtype.parent_id and subtype.parent_id.res_model == self._name:
                        new_followers.setdefault(
                            header_follower.partner_id.id, set()).add(subtype.parent_id.id)
                    elif subtype.res_model is False:
                        new_followers.setdefault(
                            header_follower.partner_id.id, set()).add(subtype.id)

        # add followers coming from res.users relational fields that are
        # tracked
        user_ids = [values[name]
                    for name in user_field_lst if values.get(name)]
        user_pids = [user.partner_id.id for user in
                     self.pool.get('res.users').browse(cr, SUPERUSER_ID, user_ids, context=context)]
        for partner_id in user_pids:
            new_followers.setdefault(partner_id, None)

        for pid, subtypes in new_followers.items():
            subtypes = list(subtypes) if subtypes is not None else None
            self.message_subscribe(
                cr, uid, ids, [pid], subtypes, context=context)

        self._message_auto_subscribe_notify(
            cr, uid, ids, user_pids, context=context)

        return True

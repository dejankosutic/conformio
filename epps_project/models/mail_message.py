# -*- coding: utf-8 -*-
##############################################################################
# This software is © copyright 2016 EPPS Services Ltd and licensed under the
# GNU Affero General Public License, version 3.0 as published by the Free
# Software Foundation.
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################

import threading
from urlparse import urljoin
from urllib import urlencode
from email.utils import formataddr
from openerp.tools import html2plaintext

from openerp.osv import fields as old_fields
from openerp import api, models, fields, SUPERUSER_ID, _, tools
from openerp.exceptions import Warning


class ResPartner(models.Model):
    _inherit = 'res.partner'
    _columns = {
        'notify_email': old_fields.selection([
            ('none', 'Never'),
            ('always', 'All Messages'),
            ('epps', 'EPPS'),
        ], 'Receive Inbox Notifications by Email', required=True,
            oldname='notification_email_send',
            help="Policy to receive emails for new messages pushed to your personal Inbox:\n"
                    "- Never: no emails are sent\n"
                    "- All Messages: for every notification you receive in your Inbox\n"
                    "- EPPS: use epps notification system"),
    }
    _defaults = {
        'notify_email': lambda *args: 'epps'
    }


class MailNotification(models.Model):
    _inherit = 'mail.notification'

    def _get_user_notification_settings(self, user):
        user_settings = {'notifications': {'message_received': user.message_received or False,
                                           'tasks_change': user.tasks_change or False,
                                           'documents_change': user.documents_change or False,
                                           'new_login': user.new_login or False,
                                           'project_invite': user.project_invite or False,
                                           'message_like': user.message_like or False,
                                           'important_updates': user.important_updates or False,
                                           },
                         'projects': [project.id for project in user.projects_to_follow]}
        return user_settings

    def epps_custom_mail_filter(self, cr, uid, ids, user_id, message, model, res_id, partner, email_pids, context=None):
        # HERE WE WILL CHECK FOR USER SETTINGS AND ACCORDINGLY APPEND USER IDS TO BE EMAILED
        user_obj = self.pool.get("res.users")
        if user_id:
            user = user_obj.browse(cr, SUPERUSER_ID, [user_id], context=context)
            user_settings = self._get_user_notification_settings(user)

        #CASE DISCUSSION
        #get comment subtype id first
        subtype_id = self.pool.get('ir.model.data').xmlid_to_res_id(cr, uid, 'mail.mt_comment')
        if user_id and message.subtype_id and message.subtype_id.id == subtype_id:
            if message.type == 'comment':
                if user_settings['notifications']['message_received']:
                    email_pids.append(partner.id)

        # CASE PROJECT
        if user_id and model == 'project.project':
            if message.type == 'notification':
                if user_settings['notifications']['project_invite']:
                    if res_id in user_settings['projects']:
                        email_pids.append(partner.id)
            """
            if message.type == 'comment':
                if user_settings['notifications']['message_received']:
                    if res_id in user_settings['projects']:
                        email_pids.append(partner.id)
            """
        # CASE TASK
        if user_id and model == 'project.task':
            project_id = self.pool.get('project.task').browse(cr, SUPERUSER_ID, [res_id], context=context)[0].project_id.id
            if message.type == 'notification':
                if user_settings['notifications']['tasks_change']:
                    if project_id in user_settings['projects']:
                        email_pids.append(partner.id)
            """
            if message.type == 'comment':
                if user_settings['notifications']['message_received']:
                    if project_id in user_settings['projects']:
                        email_pids.append(partner.id)
            """
        return email_pids

    def get_recipients(self, cr, uid, ids, message, context=None):
        # based on addons/mail/mail_followers.py::get_partners_to_email
        """ Return the list of partners to notify, based on their preferences.

            :param browse_record message: mail.message to notify
            :param list partners_to_notify: optional list of partner ids restricting
                the notifications to process
        """
        email_pids = []
        for notification in self.browse(cr, uid, ids, context=context):
            if notification.is_read:
                continue
            partner = notification.partner_id
            # Do not send to partners without email address defined
            if not partner.email:
                continue
            # Do not send to partners having same email address than the author
            # (can cause loops or bounce effect due to messy database)
            if message.author_id and message.author_id.email == partner.email:
                continue
            # Partner does not want to receive any emails or is opt-out
            n = partner.notify_email
            if n == 'none':
                continue
            if n == 'always':
                email_pids.append(partner.id)
                continue
            if n == 'epps':
                user_obj = self.pool.get("res.users")
                user = user_obj.search(
                    cr, SUPERUSER_ID, [('partner_id', '=', partner.id)], context=context)
                if user:
                    user_id = user[0]
                    if user_id:
                        model = message.model
                        res_id = message.res_id

                        email_pids = self.epps_custom_mail_filter(cr, uid, ids, user_id,
                                                                  message, model, res_id,
                                                                  partner, email_pids,
                                                                  context=context)
                continue
        return email_pids

    def _notify_email(self, cr, uid, ids, message_id, force_send=False, user_signature=True, context=None):
        # based on addons/mail/mail_followers.py::_notify_email
        message = self.pool['mail.message'].browse(
            cr, SUPERUSER_ID, message_id, context=context)

        # compute partners
        email_pids = self.get_recipients(cr, uid, ids, message, context=None)
        if context.get('from_provision', False):
            email_pids = []
        # DIRTY UPDATE PARTNERS ON MESSAGE IF MODEL IS ir.attachment
        if message.model == 'ir.attachment' and message.res_id and message.subtype_id and message.subtype_id.id:
            attachemnt = self.pool.get('ir.attachment').browse(cr,uid,[message.res_id],context=context)
            assigned_name, assigned_subtype_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'document', 'mt_document_assigned')
            approved_name, approved_subtype_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'document', 'mt_document_approved')
            partner_ids = []
            if message.subtype_id.id == assigned_subtype_id:
                partner_ids.append(attachemnt.document_next_reviewer_id and attachemnt.document_next_reviewer_id.partner_id and attachemnt.document_next_reviewer_id.partner_id.id)
            if message.subtype_id.id == approved_subtype_id:
                for user in attachemnt.notify_user_ids:
                    partner_ids.append(user.partner_id and user.partner_id.id)
            if partner_ids:
                self.pool['mail.message'].write(cr,uid,[message.id],{'notified_partner_ids':[(6,0,[partner_ids])]},context=context)
        if email_pids:
            _context = dict(context or {})
            _context.update({'mail_auto_delete':False})
            force_send = True
            if message.subtype_id and message.subtype_id.epps_subtype\
            and (message.subtype_id.email_template_id and message.subtype_id.email_template_id.id):
                template = message.subtype_id.email_template_id
                partners_to = ','.join(str(e) for e in email_pids)
                _context.update({'partners_to': partners_to})
                if message.res_id and message.res_id != 0:
                    self.send_mail_template(cr, SUPERUSER_ID, message.res_id, template, context=_context)
            if not (message.subtype_id.email_template_id and message.subtype_id.email_template_id.id)\
            and message.subtype_id and message.subtype_id.epps_subtype:
                if message.type == 'comment':
                    _context['epps_default_message'] = True
                self._do_notify_email(cr, uid, email_pids,
                                  message, force_send, user_signature, context = _context) # TODO ADD mail_auto_delete: False in context

        return True

    def send_mail_template(self, cr, uid, id, template, context=None):
        # find template 'email_temp_message_liked' (defined in xml) and send mail
        """
        ir_model_data = self.pool.get('ir.model.data')
        template_id = False
        model, template_id = ir_model_data.get_object_reference(cr, uid, 'epps_design', 'email_temp_documents_change')
        """
        template_pool = self.pool.get('email.template')
        template_id = template.id
        template_pool.send_mail(cr, SUPERUSER_ID, template_id, id, force_send=True, raise_exception=False, context=context)
        return True

    def _do_notify_email(self, cr, uid, email_pids, message, force_send=False, user_signature=True, context=None):
        # compute email body (signature, company data)
        body_html = message.body
        # add user signature except for mail groups, where users are usually
        # adding their own signatures already
        user_id = message.author_id and message.author_id.user_ids and message.author_id.user_ids[
            0] and message.author_id.user_ids[0].id or None
        #signature_company = self.get_signature_footer(cr, uid, user_id, res_model=message.model, res_id=message.res_id, context=context, user_signature=(
        #    user_signature and message.model != 'mail.group'))
        signature_company = False
        if signature_company:
            body_html = tools.append_content_to_html(
                body_html, signature_company, plaintext=False, container_tag='div')

        # compute email references
        references = message.parent_id.message_id if message.parent_id else False

        # custom values
        custom_values = dict()
        if message.model and message.res_id and self.pool.get(message.model) and hasattr(self.pool[message.model], 'message_get_email_values'):
            custom_values = self.pool[message.model].message_get_email_values(
                cr, uid, message.res_id, message, context=context)

        # create email values
        max_recipients = 50
        chunks = [email_pids[x:x + max_recipients]
                  for x in xrange(0, len(email_pids), max_recipients)]
        email_ids = []
        for chunk in chunks:
            mail_values = {
                'mail_message_id': message.id,
                # (context or {}).get('mail_auto_delete', True), # =======> DON'T AUTO DELETE MAIL
                'auto_delete': (context or {}).get('mail_auto_delete', False), # False,
                'mail_server_id': (context or {}).get('mail_server_id', False),
                'body_html': body_html,
                'recipient_ids': [(4, id) for id in chunk],
                'references': references,
            }

            mail_values.update(custom_values)

            # Override the subject and reply_to fields when a default comment is sent
            if context.get('epps_default_message', False):
                p_name = message.author_id and message.author_id.name or ""
                #res_reply_to = formataddr((p_name + ' on Conformio', 'do-not-reply@conformio.com'))
                res_reply_to = ''
                res_email_from = formataddr((p_name + ' on Conformio', 'do-not-reply@conformio.com'))
                if body_html:
                    if message.type == 'comment' and message.model != 'project.project' and message.model != 'project.task':
                        new_body = '<p>' + str(message.author_id.name or "") + _(
                            ' sent you a private message through Conformio:') + '</p>' + body_html
                        mail_values['body_html'] = new_body
                    subject = html2plaintext(str(body_html))
                    subject = " ".join(subject.split())
                    mail_values['subject'] = str(subject[:30])
                mail_values['reply_to'] = res_reply_to
                mail_values['email_from'] = res_email_from

            email_ids.append(self.pool.get('mail.mail').create(
                cr, uid, mail_values, context=context))
        # NOTE:
        #   1. for more than 50 followers, use the queue system
        #   2. do not send emails immediately if the registry is not loaded,
        #      to prevent sending email during a simple update of the database
        #      using the command-line.
        #force_send = False  # ===================================================================> DON'T SEND MAIL IMMEDIATELY
        if force_send and len(chunks) < 2 and \
            (not self.pool._init or
                getattr(threading.currentThread(), 'testing', False)):
            self.pool.get('mail.mail').send(
                cr, uid, email_ids, context=context)
        return True

    def get_signature_footer(self, cr, uid, user_id, res_model=None, res_id=None, context=None, user_signature=True):
        """ Format a standard footer for notification emails (such as pushed messages
            notification or invite emails).
            Format:
                <p>--<br />
                    Administrator
                </p>
                <div>
                    <small>Sent from <a ...>Your Company</a> using <a ...>OpenERP</a>.</small>
                </div>
        """
        footer = ""
        if not user_id:
            return footer

        # add user signature
        user = self.pool.get("res.users").browse(cr, SUPERUSER_ID, [user_id], context=context)[0]
        if user_signature:
            if user.signature:
                signature = user.signature
            else:
                signature = "--<br />%s" % user.name
            footer = tools.append_content_to_html(footer, signature, plaintext=False)

        # add company signature
        if user.company_id.website:
            website_url = ('http://%s' % user.company_id.website) if not user.company_id.website.lower().startswith(('http:', 'https:')) \
                else user.company_id.website
            company = "<a style='color:inherit' href='%s'>%s</a>" % (website_url, user.company_id.name)
        else:
            company = user.company_id.name
        sent_by = _('Sent by %(company)s') #_('Sent by %(company)s using %(odoo)s')

        signature_company = '<br /><small>%s</small>' % (sent_by % {
            'company': company,
            #'odoo': "<a style='color:inherit' href='https://www.odoo.com/'>Odoo</a>"
        })
        footer = tools.append_content_to_html(footer, signature_company, plaintext=False, container_tag='div')

        return footer


class MailMail(models.Model):
    _inherit = 'mail.mail'

    @api.cr_uid_context
    def _get_partner_access_link(self, cr, uid, mail, partner=None, context=None):
        """Generate URLs for links in mails: partner has access (is user):
        link to action_mail_redirect action that will redirect to doc or Inbox """
        if context is None:
            context = {}
        if partner and partner.user_ids:
            base_url = self.pool.get('ir.config_parameter').get_param(cr, SUPERUSER_ID, 'web.base.url')
            mail_model = mail.model or 'mail.thread'
            url = urljoin(base_url, self.pool[mail_model]._get_access_link(cr, uid, mail, partner, context=context))
            return "<span class='oe_mail_footer_access'><small>%(access_msg)s <a style='color:inherit' href='%(portal_link)s'>%(portal_msg)s</a></small></span>" % {
                'access_msg': _('about') if mail.record_name else _('access'),
                'portal_link': url,
                'portal_msg': '%s %s' % (context.get('model_name', ''), mail.record_name) if mail.record_name else _('your messages'),
            }
        else:
            return None

    def _get_epps_mail_footer(self, cr, uid, mail, partner=None, context=None):
        model = mail.model or context.get('model', False) or context.get('active_model', False) or context.get('default_model', False)
        res_id = mail.res_id or context.get('res_id', False) or context.get('active_id', False) or context.get('default_res_id', False)
        special = mail.notification or context.get('user_liked', False) or context.get('email_me', False)
        msg = ""
        link = ""
        query = {'db': cr.dbname}
        fragment = {}
        if partner:
            fragment = {'login': partner.user_ids[0].login,
                        }
        base_url = self.pool.get('ir.config_parameter').get_param(cr, SUPERUSER_ID, 'web.base.url')

        # CASE USERS
        if model == 'res.users' and res_id != 0:
            msg = "<span>The above link is only for initial confirmation of your account. In the future, for regular logging in to the network please use this link: </span>"
            #menu = self.pool.get('project.project').browse(cr, uid, [res_id], context)[0].menu_id.id
            #fragment['menu_id'] = menu
            link_end = ""
            url = urljoin(base_url, link_end)
            link = "<span><a style='color:inherit' href='%(portal_link)s'>Conformio homepage</a></span>" % {
                'portal_link': url,
            }
            #link = " PROJECT"
        # CASE PROJECT
        if model == 'project.project' and res_id != 0:
            msg = "<span class='oe_mail_footer_access'><small>See the details of the project here: <small></span>"
            menu = self.pool.get('project.project').browse(cr, uid, [res_id], context)[0].menu_id.id
            fragment['menu_id'] = menu
            link_end = "/web?%s#%s" % (urlencode(query), urlencode(fragment))
            url = urljoin(base_url, link_end)
            link = "<span class='oe_mail_footer_access'><small><a style='color:inherit' href='%(portal_link)s'>Project</a></small></span>" % {
                'portal_link': url,
            }
            #link = " PROJECT"
        # CASE TASK
        if model == 'project.task' and res_id != 0:
            msg = "<span class='oe_mail_footer_access'><small>See the details of the task here: <small></span>"
            action = self.pool.get('ir.model.data').get_object(cr, SUPERUSER_ID, 'epps_project', 'action_view_sale_task_my', context=context)
            fragment['action'] = action and action.id
            link_end = "/web?%s#%s" % (urlencode(query), urlencode(fragment))
            url = urljoin(base_url, link_end)
            link = "<span class='oe_mail_footer_access'><small><a style='color:inherit' href='%(portal_link)s'>My Tasks</a></small></span>" % {
                'portal_link': url,
            }
            #link = " MY TASKS"
        # CASE ATTACHMENT
        if model == 'ir.attachment' and res_id != 0:
            msg = "<span class='oe_mail_footer_access'><small>See the document here: <small></span>"
            action = self.pool.get('ir.model.data').get_object(cr, SUPERUSER_ID, 'epps_company_rules', 'epps_company_rules_my_files_action', context=context)
            fragment['action'] = action and action.id
            link_end = "/web?%s#%s" % (urlencode(query), urlencode(fragment))
            url = urljoin(base_url, link_end)
            if context.get('file_url', False):
                link = "<span class='oe_mail_footer_access'><small><a style='color:#027EE6;' href='%(portal_link)s'>File</a></small></span>" % {
                    'portal_link': context['file_url'],
                }
            else:
                link = "<span class='oe_mail_footer_access'><small><a style='color:inherit' href='%(portal_link)s'>My Files</a></small></span>" % {
                    'portal_link': url,
                }
            #link = " MY DOCUMENTS"
        # CASE: USER LIKES MESSAGE; EMAIL ME OPTION FROM MY DISCUSSIONS
        if special:
            msg = "<span class='oe_mail_footer_access'><small>Click here to view the message: <small></span>"
            action = self.pool.get('ir.model.data').get_object(cr, SUPERUSER_ID, 'mail', 'action_mail_inbox_feeds', context=context)
            fragment['action'] = action and action.id
            link_end = "/web?%s#%s" % (urlencode(query), urlencode(fragment))
            url = urljoin(base_url, link_end)
            link = "<span class='oe_mail_footer_access'><small><a style='color:inherit' href='%(portal_link)s'>My Discussions</a></small></span>" % {
                'portal_link': url,
            }
            #link = " MY DISCUSSIONS"

        footer = msg + link
        return footer

    def send_get_mail_body(self, cr, uid, mail, partner=None, context=None):
        """Return a specific ir_email body. The main purpose of this method
        is to be inherited to add custom content depending on some module."""
        body = mail.body_html

        # generate access links for notifications or emails linked to a specific document with auto threading
        link = None
        #if mail.notification or (mail.model and mail.res_id and not mail.no_auto_thread):
        #    link = self._get_partner_access_link(cr, uid, mail, partner, context=context)

        link = self._get_epps_mail_footer(cr, uid, mail, partner, context=context)

        if link:
            body = tools.append_content_to_html(body, link, plaintext=False, container_tag='div')
        return body

class MailMessage(models.Model):
    _inherit = 'mail.message'
    """
        If default model is project search for tasks and extend the list
        of ids and domain to show task messages within project messaging
    """

    @api.cr_uid_context
    def message_read(self, cr, uid, ids=None, domain=None, message_unload_ids=None,
                     thread_level=0, context=None, parent_id=False, limit=None):
        message_list = []
        if 'default_model' in context and context['default_model'] == 'project.project':
            project_obj = self.pool.get('project.project')
            project_id = context.get('default_res_id', False)
            task_list = []
            if project_id:
                project = project_obj.browse(cr, uid, [project_id], context)[0]
                for task in project.task_ids:
                    task_list.append(task.id)
            # must be > 1 else on message post it returns first message from
            # task and not newest message
            if task_list and ids and len(ids) > 1:
                task_domain = [('model', '=', 'project.task'),
                               ('res_id', 'in', task_list)]
                task_message_ids = self.search(
                    cr, uid, task_domain, context=context, limit=limit)
                ids = ids + task_message_ids
                domain = domain + ['|'] + task_domain
        try:
            message_list = super(MailMessage, self).message_read(cr, SUPERUSER_ID, ids, domain, message_unload_ids,
                                                             thread_level, context, parent_id, limit)
        except Exception:
            # skip SpecialValue (e.g. for missing record or access right)
            pass
        return message_list


class Project(models.Model):
    _inherit = 'project.project'

    _track = {
        'user_id': {
            'project.project_assigned': lambda self, cr, uid, obj, ctx=None: obj.user_id and obj.user_id.id,
        },
    }


    @api.multi
    def write(self, vals):
        # Update followers
        current_users = []
        for user in self.members:
            current_users.append(user.id)
        user_ids = []
        if 'members' in vals and vals['members']:
            old_members = self._get_member_names(self.members)
            for member in vals['members']:
                user_ids.extend(member[2])
            unsubscribe = [u for u in current_users if (u not in user_ids)]
            subscribe = [s for s in user_ids if (s not in current_users)]
            # remove users from group, or add them
            for u in unsubscribe:
                self.group_id.sudo().write({'users': [(3, u)]})
                user_obj = self.env['res.users']
                users = user_obj.browse([u])
                for user in users:
                    user.sudo().write({'projects_to_follow': [(3, self.id)]})
            for s in subscribe:
                self.group_id.sudo().write({'users': [(4, s)]})
                user_obj = self.env['res.users']
                users = user_obj.browse([s])
                for user in users:
                    user.sudo().write({'projects_to_follow': [(4, self.id)]})
            # Automaticly add all team members of project to message followers
            self.message_unsubscribe_users(user_ids=unsubscribe)
            self.message_subscribe_users(user_ids=subscribe, subtype_ids=None)

        res = super(Project, self).write(vals)
        if 'members' in vals:
            new_members = self._get_member_names(self.members)
            self.message_post(
                body="<b>Members Changed:</b> %s &#8594; %s" % (old_members, new_members),
                subtype='project.project_members_assigned')
        return res

    def _get_member_names(self, members):
        return ', '.join([user.name for user in members])

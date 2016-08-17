# -*- coding: utf-8 -*-
##############################################################################
# This software is © copyright 2016 EPPS Services Ltd and licensed under the
# GNU Affero General Public License, version 3.0 as published by the Free
# Software Foundation.
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################

from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
import re
from openerp import SUPERUSER_ID
from lxml import etree
from lxml.builder import E
from openerp.addons.base.res.res_users import name_boolean_group, name_selection_groups
import logging
_logger = logging.getLogger(__name__)

class ResUsers(models.Model):
    _inherit = 'res.users'

    def default_get(self, cr, uid, fields, context=None):
        res = super(ResUsers, self).default_get(
            cr, uid, fields, context=context)
        for k, v in res.iteritems():
            if k.startswith('sel_groups_'):
                get_id = k.split("_")
                id = get_id[2]
                res[k] = int(id)

        # Set the default values of the fields on create since compute works only in edit mode.
        # We need to skip this step when installing the module
        company_id = self._get_company(cr, uid)
        if company_id and not context.get('install_mode', False):
            company_obj = self.pool.get('res.company').browse(cr, uid, company_id, context=context)
            if company_obj and company_obj.max_number_of_users:
                res['max_number_of_users'] = company_obj.max_number_of_users
            if company_obj and company_obj.number_of_users:
                res['number_of_users'] = company_obj.number_of_users
            if company_obj and company_obj.remaining_users:
                res['remaining_users'] = company_obj.remaining_users
        return res

    def fields_get(self, cr, uid, allfields=None, context=None, write_access=True, attributes=None):
        res = super(ResUsers, self).fields_get(
            cr, uid, allfields, context, write_access, attributes)
        # add reified groups fields
        if uid != SUPERUSER_ID and not (self.pool['res.users'].has_group(cr, uid, 'base.group_erp_manager')
                                        or self.pool['res.users'].has_group(cr, uid, 'epps_user.group_customer_administrator')):
            return res
        for app, kind, gs in self.pool['res.groups'].get_groups_by_application(cr, uid, context):
            if kind == 'selection':
                # selection group field
                tips = ['%s: %s' % (g.name, g.comment)
                        for g in gs if g.comment]

                res[name_selection_groups(map(int, gs))] = {
                    'type': 'selection',
                    'string': app and app.name or _('Other'),
                    'selection': [(False, '')] + [(g.id, g.name) for g in gs],
                    'help': '\n'.join(tips),
                    'exportable': False,
                    'selectable': False,
                }
            else:
                # boolean group fields
                for g in gs:
                    res[name_boolean_group(g.id)] = {
                        'type': 'boolean',
                        'string': g.name,
                        'help': g.comment,
                        'exportable': False,
                        'selectable': False,
                    }
        return res

    id = fields.Integer('Id', readonly=True)
    customer_administrator = fields.Boolean('Customer Administrator')
    max_number_of_users = fields.Integer(
        string='Max. users',
        compute='_get_num_of_users',
        store=False,
        help='Maximum number of users',
        readonly=True)

    number_of_users = fields.Integer(
        string='Users',
        compute='_get_num_of_users',
        store=False,
        help='Number of users',
        readonly=True)

    remaining_users = fields.Integer(
        string='Remaining users',
        compute='_get_num_of_users',
        store=False,
        help='Remaining number of users',
        readonly=True)

    message_received = fields.Boolean("1) I receive a message", default=True)
    tasks_change = fields.Boolean(
        "2) I get new tasks or status of my tasks changes", default=True)
    documents_change = fields.Boolean(
        "3) Documents to which I'm subscribed changes", default=True)
    new_login = fields.Boolean("4) I login from somewhere new", default=True)
    project_invite = fields.Boolean("5) Someone invites me to a Project", default=True)
    message_like = fields.Boolean("6) Someone likes a message I posted", default=True)
    important_updates = fields.Boolean(
        "7) Important updates about Conformio features available", default=True)

    _email_max_26_re = re.compile(
        r"""^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,26}$""", re.VERBOSE)

    def __init__(self, pool, cr):
        """ Override of __init__ to add access rights on notification_email_send
            and alias fields. Access rights are disabled by default, but allowed
            on some specific fields defined in self.SELF_{READ/WRITE}ABLE_FIELDS.
        """
        init_res = super(ResUsers, self).__init__(pool, cr)
        # duplicate list to avoid modifying the original reference
        self.SELF_WRITEABLE_FIELDS = list(self.SELF_WRITEABLE_FIELDS)
        self.SELF_WRITEABLE_FIELDS.extend(['message_received', 'tasks_change',
                                           'documents_change', 'new_login',
                                           'project_invite', 'message_like',
                                           'important_updates'
                                           ])
        # duplicate list to avoid modifying the original reference
        self.SELF_READABLE_FIELDS = list(self.SELF_READABLE_FIELDS)
        self.SELF_READABLE_FIELDS.extend(['message_received', 'tasks_change',
                                           'documents_change', 'new_login',
                                           'project_invite', 'message_like',
                                           'important_updates'
                                           ])
        return init_res

    @api.onchange('firstname', 'lastname')
    def change_name(self):
        names = [name for name in [self.firstname, self.lastname] if name]
        self.name = ' '.join(names)

    def on_change_login(self, cr, uid, ids, login, context=None):
        if login and self.check_login(login):
            return {'value': {'email': login}}
        return {}

    @api.model
    def create(self, values):
        login = values.get('login', False)
        if not self._context or self._context.get('install_mode'):
            return super(ResUsers, self).create(values)
        if login:
            self.check_login(login)
        company_id = values.get('company_id', False)
        if company_id:
            self.check_number_of_users(company_id)
        return super(ResUsers, self).create(values)

    @api.multi
    def write(self, values):
        login = values.get('login', False)
        old_login = self.login
        if login and (self._uid != SUPERUSER_ID):
            self.check_login(login)
        if values.get('active') or values.get('share'):
            self.check_number_of_users(self.company_id.id)
        ret = super(ResUsers, self).write(values)
        if login and old_login == "customeradmin@example.com":
            ctx = self._context.copy()
            ctx.update({'create_user': 1})
            try:
                self.with_context(ctx).action_reset_password()
            except Exception, e:
                _logger.warning(
                    "Unable to send mail to customer admin, this is what we get %s." % (e))
        return ret


    @api.multi
    def unlink(self):
        for user in self:
            customer_admin = user.env.ref('base.user_customer_administrator')
            if user == customer_admin:
                raise Warning(
                    _("You can't delete user: %s, as it is customer admin!") % customer_admin.name)
        return super(ResUsers, self).unlink()

    @api.model
    def get_reseller_logo_id(self):
        res = self.env['ir.config_parameter'].get_param('epps.reseller_logo_id') or ''
        return res

    def check_login(self, login):
        res = self._email_max_26_re.match(login)
        check_copy = login.endswith('(copy)')
        if check_copy:
            res = True
        if not res:
            raise Warning(
                _('Email address has an invalid format please recheck it.'))
        return res

    @api.multi
    def check_number_of_users(self, company_id):
        company_obj = self.env['res.company']
        company = company_obj.browse([company_id])
        if company.remaining_users <= 0:
            raise Warning(
                _("You've exceeded the maximum number of users for company selected."))
        return True

    @api.multi
    def update_active(self):
        for user in self:
            if not user.active:
                user.write({'active': True})
            elif user.active:
                user.write({'active': False})
        return True

    @api.one
    @api.depends('company_id')
    def _get_num_of_users(self):
        company = self.company_id
        if not company:
            self.max_number_of_users = 0
            self.number_of_users = 0
        if company:
            self.max_number_of_users = company.max_number_of_users
            self.number_of_users = company.number_of_users
            self.remaining_users = company.remaining_users

    def notifications_save(self, cr, uid, ids, context=None):
        return {
            'type': 'ir.actions.client',
            'tag': 'reload_context',
        }

    # completely overriding the original function because we need to remove token expiration date.
    def action_reset_password(self, cr, uid, ids, context=None):
        """ create signup token for each user, and send their signup url by email """
        # prepare reset password signup
        res_partner = self.pool.get('res.partner')
        partner_ids = [user.partner_id.id for user in self.browse(cr, uid, ids, context)]
        # completely overriding the original function because we need to remove token expiration date.
        res_partner.signup_prepare(cr, uid, partner_ids, signup_type="reset", expiration=False, context=context)

        context = dict(context or {})

        # send email to users with their signup url
        template = False
        if context.get('create_user'):
            try:
                # get_object() raises ValueError if record does not exist
                template = self.pool.get('ir.model.data').get_object(cr, uid, 'auth_signup', 'set_password_email')
            except ValueError:
                pass
        if not bool(template):
            template = self.pool.get('ir.model.data').get_object(cr, uid, 'auth_signup', 'reset_password_email')
        assert template._name == 'email.template'

        for user in self.browse(cr, uid, ids, context):
            if not user.email:
                raise Warning(_("Cannot send email: user has no email address. %s") % (user.name))
            context['lang'] = user.lang  # translate in targeted user language
            self.pool.get('email.template').send_mail(cr, uid, template.id, user.id, force_send=True, raise_exception=True, context=context)

class GroupsView(models.Model):
    _inherit = 'res.groups'
    _order = 'category_id,name'

    group_admin_id = fields.Many2one(
        'res.users', string='Project Group Administrator')

    def update_user_groups_view(self, cr, uid, context=None):
        res = super(GroupsView, self).update_user_groups_view(
            cr, uid, context=context)

        if not context or context.get('install_mode'):
            # use installation/admin language for translatable names in the
            # view
            context = dict(context or {})
            context.update(self.pool['res.users'].context_get(cr, uid))
        view = self.pool['ir.model.data'].xmlid_to_object(
            cr, SUPERUSER_ID, 'epps_user.epps_user_groups_view', context=context)
        epps_modules_category = self.pool['ir.model.data'].xmlid_to_object(
            cr, SUPERUSER_ID, 'base.module_category_epps_modules', context=context)
        if view and view.exists() and view._name == 'ir.ui.view':
            xml1, xml2 = [], []
            xml1.append(E.separator(string=_('Modules'), colspan="1"))
            xml1.append(E.separator(string=_('Access Rights'), colspan="1"))
            xml1.append(E.separator(string=_(''), colspan="2"))
            for app, kind, gs in self.get_groups_by_application(cr, uid, context):
                if app and app.parent_id and app.parent_id.id == epps_modules_category.id and app.visible != False:
                    # hide groups in category 'Hidden' (except to group_no_one)
                    attrs = {
                        'groups': 'base.group_no_one'} if app and app.xml_id == 'base.module_category_hidden' else {}
                    if kind == 'selection':
                        # application name with a selection field
                        field_name = name_selection_groups(map(int, gs))
                        xml1.append(E.field(name=field_name, **attrs))
                        xml1.append(E.newline())
                    else:
                        # application separator with boolean fields
                        app_name = app and app.name or _('Other')
                        xml2.append(E.separator(
                            string=app_name, colspan="4", **attrs))
                        for g in gs:
                            field_name = name_boolean_group(g.id)
                            xml2.append(E.field(name=field_name, **attrs))

            xml = E.field(*(xml1 + xml2), name="groups_id", position="replace")
            xml.addprevious(etree.Comment("GENERATED AUTOMATICALLY BY GROUPS"))
            xml_content = etree.tostring(
                xml, pretty_print=True, xml_declaration=True, encoding="utf-8")
            view.write({'arch': xml_content})
        return res

# -*- coding: utf-8 -*-
##############################################################################
# This software is © copyright 2016 EPPS Services Ltd and licensed under the
# GNU Affero General Public License, version 3.0 as published by the Free
# Software Foundation.
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################

from openerp import models, fields, api, _, modules
from openerp.exceptions import Warning
from openerp import SUPERUSER_ID
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
import pytz
from dateutil import parser
from dateutil import rrule
from datetime import datetime, timedelta
import re
import operator
import itertools
from openerp.tools import html2plaintext


class ProjectTask(models.Model):
    _inherit = 'project.task'
    _mail_flat_thread = False
    _track = {
        'done': {
            'project.mt_task_done': lambda self, cr, uid, obj, ctx=None: obj.done,
        },
        'user_id': {
            'project.mt_task_assigned': lambda self, cr, uid, obj, ctx=None: obj.user_id and obj.user_id.id,
        }
    }

    # add this to all m2o res_user domain=[('id', '!=', SUPERUSER_ID)]
    # remove track_visibility
    kanban_state = fields.Selection(track_visibility=False)
    stage_id = fields.Many2one(track_visibility=False)
    name = fields.Char(track_visibility=False)
    date_deadline = fields.Date(track_visibility='onchange')

    done = fields.Boolean('Done', help="Task Done")
    is_section = fields.Boolean('Section', help="Section to separate tasks")

    # original definition
    # 'reviewer_id': fields.many2one('res.users', 'Reviewer', select=True,
    #                               track_visibility='onchange'),
    reviewer_id = fields.Many2one( # remove default
        #'res.users',
        default=lambda self: self.env[
            'res.users'].browse(
            self._context.get('reviewer_id', False)))
    assigned_by_id = fields.Many2one('res.users', 'Assigned By')

    # RECURRENCE FIELDS
    rrule = fields.Char(compute="_get_rulestring",
                        inverse="_set_rulestring", store=True, string='Recurrent Rule')
    rrule_type = fields.Selection([('daily', 'Daily'), ('weekly', 'Weekly'), ('monthly', 'Monthly'), (
        'yearly', 'Yearly')], 'Recurrency', help="Let the event automatically repeat at that interval")
    recurrency = fields.Boolean('Recurrent', help="Recurrent Meeting")
    recurrent_id = fields.Integer('Recurrent ID')
    recurrent_id_date = fields.Datetime('Recurrent ID date')
    end_type = fields.Selection(
        [('count', 'Number of repetitions'),
         ('end_date', 'End date')
         ],
        string='Recurrence Termination',
        default='count'
    )
    interval = fields.Integer(
        'Repeat Every', help="Repeat every (Days/Week/Month/Year)")
    interval_12 = fields.Selection([('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5'), ('6', '6'), ('7', '7'), (
        '8', '8'), ('9', '9'), ('10', '10'), ('11', '11'), ('12', '12')], 'Interval', help="Repeat every (Days/Week/Month/Year)")
    count = fields.Integer('Repeat', help="Repeat x times", default=1)
    mo = fields.Boolean('Mon')
    tu = fields.Boolean('Tue')
    we = fields.Boolean('Wed')
    th = fields.Boolean('Thu')
    fr = fields.Boolean('Fri')
    sa = fields.Boolean('Sat')
    su = fields.Boolean('Sun')
    month_by = fields.Selection([('date', 'Date of month'), ('day', 'Day of month')], 'Option',
                                oldname='select1')
    day = fields.Integer('Date of month')
    day_28 = fields.Selection([('1', '1st'),
                               ('2', '2nd'),
                               ('3', '3rd'),
                               ('4', '4th'),
                               ('5', '5th'),
                               ('6', '6th'),
                               ('7', '7th'),
                               ('8', '8th'),
                               ('9', '9th'),
                               ('10', '10th'),
                               ('11', '11th'),
                               ('12', '12th'),
                               ('13', '13th'),
                               ('14', '14th'),
                               ('15', '15th'),
                               ('16', '16th'),
                               ('17', '17th'),
                               ('18', '18th'),
                               ('19', '19th'),
                               ('20', '20th'),
                               ('21', '21th'),
                               ('22', '22th'),
                               ('23', '23th'),
                               ('24', '24th'),
                               ('25', '25th'),
                               ('26', '26th'),
                               ('27', '27th'),
                               ('28', '28th'),
                               ('last', 'last')],
                              'Interval',
                              help="Repeat every (Days/Week/Month/Year)")
    week_list = fields.Selection([('MO', 'Monday'), ('TU', 'Tuesday'), ('WE', 'Wednesday'),
                                  ('TH', 'Thursday'), ('FR',
                                                       'Friday'), ('SA', 'Saturday'),
                                  ('SU', 'Sunday')], 'Weekday')
    byday = fields.Selection([('1', 'First'), ('2', 'Second'), ('3', 'Third'),
                              ('4', 'Fourth'), ('5', 'Fifth'), ('-1', 'Last')],
                             'By day')
    final_date = fields.Date('Repeat Until')
    active = fields.Boolean(compute='_is_template', store=True,
                            string='Not a Template Task',
                            help="This field is computed automatically and have the same behavior than the boolean 'active' field: if the task is linked to a template or unactivated project, it will be hidden unless specifically asked.")

    # Simple subtasks self relations
    parent_task_id = fields.Many2one(
        string='Parent task',
        comodel_name='project.task',
        index=True, ondelete='restrict'
    )
    subtask_ids = fields.One2many(comodel_name='project.task', inverse_name='parent_task_id',
                                  string='Subtasks')

    _defaults = {
        'user_id': False,
        'count': 1,
        'end_type': 'count',
        'month_by': 'date'
    }

    @api.model
    def create(self, values):
        name = values.get('name', False)
        if name:
            if name.endswith(':'):
                values['is_section'] = True
        assigned_user_id = values.get('user_id', False)

        if assigned_user_id:
            values['assigned_by_id'] = self._uid
        return super(ProjectTask, self).create(values)

    @api.one
    def write(self, values):
        name = values.get('name', False)
        if name:
            if name.endswith(':'):
                values['is_section'] = True
        assigned_user_id = values.get('user_id', False)

        if assigned_user_id:
            values['assigned_by_id'] = self._uid
        return super(ProjectTask, self).write(values)

    @api.multi
    def copy(self, default=None):
        if default is None:
            default = {}

        default['user_id'] = None
        default['reviewer_id'] = None
        res = super(ProjectTask, self).copy(default)
        sub_tasks = self.env['project.task'].search([('parent_task_id', '=', self.id)])
        if sub_tasks:
            default.clear()
            default['parent_task_id'] = res.id
            default['user_id'] = None
            default['reviewer_id'] = None
            for task in sub_tasks:
                default['name'] = task.name or ''
                task.copy(default)

        return res

    @api.multi
    def delete_task_recoursivly(self, removed_tasks):
        sub_tasks = self.env['project.task'].search([('parent_task_id', '=', self.id)])
        if sub_tasks:
            for _task in sub_tasks:
                removed_tasks = _task.delete_task_recoursivly(removed_tasks)
            self.unlink()
            removed_tasks.append(self.id)
        else:
            self.unlink()
            removed_tasks.append(self.id)
        return removed_tasks

    @api.onchange('rrule_type')
    def update_interval(self):
        if self.rrule_type == 'daily' or self.rrule_type == 'yearly':
            self.interval = 1
        else:
            self.interval = 0

    @api.onchange('interval_12')
    def update_interval_weekly(self):
        self.interval = self.interval_12

    @api.onchange('day_28')
    def update_day_monthly(self):
        if self.day_28 != 'last':
            self.day = self.day_28
        else:
            self.day = 28

    @api.multi
    @api.depends('byday', 'recurrency', 'final_date', 'rrule_type', 'month_by',
                 'interval', 'count', 'end_type', 'mo', 'tu', 'we', 'th', 'fr', 'sa',
                 'su', 'day', 'week_list')
    def _get_rulestring(self):
        for id in self.ids:
            data = {'id': self.id,
                    'byday': self.byday,
                    'recurrency': self.recurrency,
                    'final_date': self.final_date,
                    'rrule_type': self.rrule_type,
                    'month_by': self.month_by,
                    'interval': self.interval,
                    'count': self.count,
                    'end_type': self.end_type,
                    'mo': self.mo, 'tu': self.tu, 'we': self.we, 'th': self.th, 'fr': self.fr, 'sa': self.sa, 'su': self.su,
                    'day': self.day,
                    'week_list': self.week_list}

            if data['recurrency']:
                self.rrule = self.compute_rule_string(data)
            else:
                self.rrule = ''

    @api.multi
    def _set_rulestring(self):
        data = self._get_empty_rrule_data()
        rdate = self.date_deadline
        if self.rrule and rdate:
            data['recurrency'] = True
            update_data = self._parse_rrule(self.rrule, dict(data), rdate)
            data.update(update_data)
            self.write(data)
        return True

    @api.one
    @api.depends('project_id', 'done')
    def _is_template(self):
        self.active = True
        if self.project_id:
            if self.project_id.active == False or self.project_id.state == 'template':
                self.active = False
        if self.done == True:
            self.active = False

    def get_recurrent_date_for_task(self):
        """Get recurrent dates based on Rule string
        """
        context = self._context.copy()
        timezone = pytz.timezone(context.get('tz') or 'UTC')
        startdate = timezone.localize(datetime.now())
        startdate = startdate.astimezone(timezone)
        rset1 = rrule.rrulestr(
            str(self.rrule), dtstart=startdate, forceset=True)
        return [d.astimezone(pytz.UTC) for d in rset1]

    @api.multi
    def button_done(self):
        for task in self:
            if task.rrule:
                rdates = task.get_recurrent_date_for_task()
                date = rdates[0]
                # TODO CALL CREATE NEW TASK WITH DATE
                # print date
                newTask = task.copy()
                newTask.date_deadline = date
                newTask.name = task.name  # to avoid (copy) suffix

            task.done = True

    @api.multi
    def button_undone(self):
        for task in self:
            task.done = False

    @api.multi
    def button_details(self):
        context = self.env.context.copy()
        view_id = self.env.ref(
            'epps_project.'
            'epps_view_task_form2').id
        context['view_buttons'] = True
        context['parent'] = self.project_id.id
        context['task_ids'] = self.project_id.task_ids.mapped('id')
        context['self_id'] = self.id

        view = {
            'name': _(''),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'project.task',
            'view_id': view_id,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'readonly': True,
            'res_id': self.id,
            'context': context,
        }
        return view

    @api.multi
    def previous_task(self):
        return {'type': 'ir.actions.act_window.prev'}

    @api.multi
    def next_task(self):
        return {'type': 'ir.actions.act_window.next'}

    @api.model
    def compute_rule_string(self, data):
        if data['interval'] and data['interval'] < 0:
            raise Warning(_('warning!'), _('interval cannot be negative.'))
        if data['count'] and data['count'] <= 0:
            raise Warning(_('warning!'), _('count cannot be negative or 0.'))

        def get_week_string(freq, data):
            weekdays = ['mo', 'tu', 'we', 'th', 'fr', 'sa', 'su']
            if freq == 'weekly':
                byday = map(lambda x: x.upper(), filter(
                    lambda x: data.get(x) and x in weekdays, data))
                if byday:
                    return ';BYDAY=' + ','.join(byday)
            return ''

        def get_month_string(freq, data):
            if freq == 'monthly':
                if data.get('month_by') == 'date' and (data.get('day') < 1 or data.get('day') > 31):
                    raise Warning(
                        _('Error!'), ("Please select a proper day of the month."))

                if data.get('month_by') == 'day':  # Eg : Second Monday of the month
                    return ';BYDAY=' + data.get('byday') + data.get('week_list')
                elif data.get('month_by') == 'date':  # Eg : 16th of the month
                    return ';BYMONTHDAY=' + str(data.get('day'))
            return ''

        def get_end_date(data):
            if data.get('final_date'):
                data['end_date_new'] = ''.join(
                    (re.compile('\d')).findall(data.get('final_date'))) + 'T235959Z'

            return (data.get('end_type') == 'count' and (';COUNT=' + str(data.get('count'))) or '') +\
                ((data.get('end_date_new') and data.get('end_type') ==
                  'end_date' and (';UNTIL=' + data.get('end_date_new'))) or '')

        freq = data.get('rrule_type', False)  # day/week/month/year
        res = ''
        if freq:
            interval_srting = data.get('interval') and (
                ';INTERVAL=' + str(data.get('interval'))) or ''
            res = 'FREQ=' + freq.upper() + get_week_string(freq, data) + interval_srting + \
                get_end_date(data) + get_month_string(freq, data)

        return res

    @api.model
    def _get_empty_rrule_data(self):
        return {
            'byday': False,
            'recurrency': False,
            'final_date': False,
            'rrule_type': False,
            'month_by': False,
            'interval': 0,
            'count': False,
            'end_type': False,
            'mo': False,
            'tu': False,
            'we': False,
            'th': False,
            'fr': False,
            'sa': False,
            'su': False,
            'day': False,
            'week_list': False
        }

    @api.model
    def _parse_rrule(self, rule, data, date_start):
        day_list = ['mo', 'tu', 'we', 'th', 'fr', 'sa', 'su']
        rrule_type = ['yearly', 'monthly', 'weekly', 'daily']
        r = rrule.rrulestr(
            rule, dtstart=datetime.strptime(date_start, '%Y-%m-%d'))

        if r._freq > 0 and r._freq < 4:
            data['rrule_type'] = rrule_type[r._freq]
        data['count'] = r._count
        data['interval'] = r._interval
        data['final_date'] = r._until and r._until.strftime('%Y-%m-%d')
        # repeat weekly
        if r._byweekday:
            for i in xrange(0, 7):
                if i in r._byweekday:
                    data[day_list[i]] = True
            data['rrule_type'] = 'weekly'
        # repeat monthly by nweekday ((weekday, weeknumber), )
        if r._bynweekday:
            data['week_list'] = day_list[r._bynweekday[0][0]].upper()
            data['byday'] = str(r._bynweekday[0][1])
            data['month_by'] = 'day'
            data['rrule_type'] = 'monthly'

        if r._bymonthday:
            data['day'] = r._bymonthday[0]
            data['month_by'] = 'date'
            data['rrule_type'] = 'monthly'

        # repeat yearly but for openerp it's monthly, take same information as
        # monthly but interval is 12 times
        if r._bymonth:
            data['interval'] = data['interval'] * 12

        # FIXEME handle forever case
        # end of recurrence
        # in case of repeat for ever that we do not support right now
        if not (data.get('count') or data.get('final_date')):
            data['count'] = 100
        if data.get('count'):
            data['end_type'] = 'count'
        else:
            data['end_type'] = 'end_date'
        return data

    # TODO This is POC version, rewrite
    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False, lazy=True):
        result = []
        if groupby and groupby[0] == "date_deadline:gtd_interval":
            # GET DATES TO WORK WITH
            get_dates = """SELECT CURRENT_DATE as today, (CURRENT_DATE  + interval '7 days')::date as week"""
            cr.execute(get_dates)
            today_week = cr.dictfetchone()
            # GET GROUPBY WITH DATES FROM UPPER QUERY
            # MAYBE ADD date_deadline < today FOR  TASKS THAT HAVE PASSED THEIR
            # DEADLINE ???
            query = self._where_calc(cr, uid, domain, context=context)
            from_clause, where_clause, where_clause_params = query.get_sql()
            prefix_terms = lambda prefix, terms: (
                prefix + " " + ",".join(terms)) if terms else ''
            prefix_term = lambda prefix, term: (
                '%s %s' % (prefix, term)) if term else ''
            query = """
                     SELECT
                        min (project_task.id ) AS id
                       ,count (project_task.id ) AS date_deadline_count --, date_trunc('month', "project_task"."date_deadline") AS "date_deadline:month"
                       ,CASE
                            WHEN "project_task"."date_deadline" IS NULL
                                THEN 'New'
                            WHEN "project_task"."date_deadline" <= '%(today)s' --to DO igra s datumom i utc-om
                                THEN 'Today'
                            WHEN "project_task"."date_deadline"  > '%(today)s' AND "project_task"."date_deadline" <= '%(week)s' --to DO igra s datumom i utc-om
                                THEN 'Upcoming'
                            WHEN "project_task"."date_deadline" > '%(week)s' --to DO igra s datumom i utc-om
                                THEN 'Later'
                            ELSE 'Later'
                        END AS "date_deadline:gtd_interval"
                    FROM
                        "project_task" --WHERE ((("project_task"."active" = TRUE)  AND  ("project_task"."user_id" = 1))  AND  ("project_task"."user_id" = 1))
                         %(where)s
                    GROUP BY
                        CASE
                            WHEN "project_task"."date_deadline" IS NULL
                                THEN 'New'
                            WHEN "project_task"."date_deadline" <= '%(today)s' --to DO igra s datumom i utc-om
                                THEN 'Today'
                            WHEN "project_task"."date_deadline"  > '%(today)s' AND "project_task"."date_deadline" <= '%(week)s' --to DO igra s datumom i utc-om
                                THEN 'Upcoming'
                            WHEN "project_task"."date_deadline" > '%(week)s' --to DO igra s datumom i utc-om
                                THEN 'Later'
                            ELSE 'Later'
                        END
                     """ % {
                'today': today_week['today'],
                'week': today_week['week'],
                'where': prefix_term('WHERE', where_clause),
            }
            cr.execute(query, where_clause_params)
            fetched_data = cr.dictfetchall()

            # MAP DOMAINS TO BE ADDED TO GROUP BY
            add_domain = {'New': [('date_deadline', '=', None)],
                          'Today': [('date_deadline', '<=', today_week['today'])],
                          'Upcoming': [('date_deadline', '>', today_week['today'])] + [('date_deadline', '<=', today_week['week'])],
                          'Later': [('date_deadline', '>', today_week['week'])],
                          }
            # CHANGE THE ID TO SORT THINGS AS NEEDED
            reorder_id = {'New': 1,
                          'Today': 2,
                          'Upcoming': 3,
                          'Later': 4,
                          }
            if fetched_data:
                result = [{
                    '__context': {'group_by': groupby[1:]},
                    '__domain': domain + add_domain[line['date_deadline:gtd_interval']],
                    'date_deadline_count': line['date_deadline_count'],
                    'date_deadline:gtd_interval': line['date_deadline:gtd_interval'],
                    'id': reorder_id[line['date_deadline:gtd_interval']]
                } for line in fetched_data]
            # SORT THE DATA OVER ID
            result = sorted(
                result, key=operator.itemgetter('id'), reverse=False)
            # RETURN DATA GROUPED
            return result
        else:
            return super(ProjectTask, self).read_group(cr, uid, domain, fields, groupby, offset=offset,
                                                       limit=limit, context=context, orderby=orderby, lazy=lazy)

    @api.multi
    def button_save_data(self):
        return True


class ProjectPad(models.Model):
    _name = 'project.pad'
    _inherit = ['pad.common']

    name = fields.Char(string='Note name')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting_approval', 'Waiting for approval'),
        ('approved', 'Approved'),
        ('canceled', 'Cancelled'),
    ], string='State', default='draft', track_visibility='onchange')
    project_id = fields.Many2one('project.project', 'Project')
    author_user_id = fields.Many2one('res.users', 'Author')
    approve_user_id = fields.Many2one('res.users', 'Approver')
    note = fields.Char('Note')
    note_pad = fields.Char('Note', pad_content_field='note')

    @api.multi
    def previous_pad(self):
        return {'type': 'ir.actions.act_window.page.prev'}

    @api.multi
    def next_pad(self):
        return {'type': 'ir.actions.act_window.page.next'}


class IrUiMenu(models.Model):
    _inherit = ['ir.ui.menu']

    icon_file = fields.Char('Icon File')


class Project(models.Model):
    _name = 'project.project'
    _inherit = ['project.project']
    _mail_flat_thread = False

    group_id = fields.Many2one('res.groups', string='Related Group')
    menu_id = fields.Many2one('ir.ui.menu', string='Related Menu')
    pad_ids = fields.One2many('project.pad', 'project_id', string='Notes')
    task_ids = fields.One2many('project.task', 'project_id', string='Tasks')
    project_attachments = fields.Many2many('ir.attachment',
                                           'project_attachment_ids_rel',
                                           'project_id', 'attachment_id', 'Attacments')
    state = fields.Selection([('template', 'Template'),
                              ('draft', 'New'),
                              ('open', 'In Progress'),
                              ('cancelled', 'Cancelled'),
                              ('pending', 'Pending'),
                              ('close', 'Closed')],
                             'Status', required=True, copy=False, default='draft')
    project_description = fields.Text(string='Project description')
    project_description_txt = fields.Char(
        string='Project description', compute='_compute_project_description_txt')

    privacy_visibility = fields.Selection(help=False)

    ids_4_discussions = fields.Integer(
        string="ID for discussions", compute='_getid')
    messages_4_discussions = fields.One2many(
        'mail.message', string="messages_4_discussions", compute='_getmsg')
    messages_4_recentdiscussions = fields.One2many('mail.message', string="messages_4_recentdiscussions",
                                                   compute='_getmsgrec')
    messages_4_recenttasks = fields.One2many(
        'mail.message', string="messages_4_recenttasks", compute='_getmsgrectask')
    messages_4_recentfiles = fields.One2many(
        'mail.message', string="messages_4_recenttasks", compute='_getmsgrecfiles')

    # tools.html2plaintext(body)
    @api.multi
    def _getid(self):
        for project in self:
            project.ids_4_discussions = project.id

    @api.multi
    def _getmsg(self):
        for project in self:
            project.messages_4_discussions = project.message_ids

    @api.multi
    def _getmsgrec(self):
        for project in self:
            project.messages_4_recentdiscussions = project.message_ids

    def get_messages_for_recent_discussions(self, cr, uid, res_id, context=None):
        if context is None:
            context = {}
        context.update({'active_test':False})
        mail_message = self.pool['mail.message']
        pt = self.pool['project.task']
        i = self.pool['ir.attachment']
        t_ids = pt.search(cr, uid, [('project_id', '=', res_id)], context=context)
        msg_ids = mail_message.search(
            cr, uid, [('res_id', 'in', t_ids), ('model', '=', 'project.task')], order='date')
        msg_ids.extend(mail_message.search(
            cr, uid, [('res_id', '=', res_id), ('model', '=', 'project.project')]))
        a_ids = i.search(cr, uid, [('res_id', '=', res_id), ('res_model', '=', 'project.project')], order='write_date')
        msg_ids.extend(mail_message.search(cr, uid, [('res_id', 'in', a_ids)]))
        return msg_ids

    @api.multi
    def _getmsgrectask(self):
        for project in self:
            project.messages_4_recenttasks = project.message_ids

    @api.multi
    def _getmsgrecfiles(self):
        for project in self:
            project.messages_4_recentfiles = project.message_ids

    def get_messages_for_attachment(self, cr, uid, res_id, context=None):
        if context is None:
            context = {}
        context.update({'active_test':False})
        msg_ids = []
        pt = self.pool['project.task']
        t_ids = pt.search(cr, uid, [('project_id', '=', res_id)], context=context)
        i = self.pool['ir.attachment']
        a_ids = i.search(cr, uid, [
                         ('res_id', 'in', t_ids), ('res_model', '=', 'project.task')], order='write_date')
        a_ids.extend(
            i.search(cr, uid, [('res_id', '=', res_id), ('res_model', '=', 'project.project')], order='write_date'))
        if a_ids:
            mail_message = self.pool['mail.message']
            msg_ids = mail_message.search(cr, uid, [('res_id', 'in', a_ids)])
            return msg_ids
        return []

    def get_messages_from_tags(self, cr, uid, tag, res_id, context=None):
        message_tags = self.pool['message.tags']
        mail_message = self.pool['mail.message']
        tag_ids = message_tags.search(cr, uid, [('tag', '=', tag)])
        if len(tag_ids) > 0:
            message_ids = mail_message.search(
                cr, uid, [['message_tags_ids', 'in', tag_ids], ['res_id', '=', res_id]])
            if len(message_ids) > 0:
                return message_ids
        return []

    @api.one
    @api.depends('project_description')
    def _compute_project_description_txt(self):
        self.project_description_txt = html2plaintext(
            self.project_description) if self.project_description else ''

    @api.model
    def create(self, vals):
        #do not create a new menu for project company_rules
        if vals.get('is_company_rules', False):
            return super(Project, self).create(vals)
        # do not create a new menu for project my_files
        if vals.get('is_my_files', False):
            return super(Project, self).create(vals)
        # do not create a new menu for project_repository
        if vals.get('is_repository', False):
            return super(Project, self).create(vals)
        # do not create a new menu for conbase modules
        if vals.get('is_conbase', False):
            return super(Project, self).create(vals)
        # get parent menu
        menu_parent = self.env['ir.model.data'].get_object_reference('epps_project',
                                                                     'epps_menu_project_management')
        menu_parent = menu_parent and menu_parent[1] or False
        # Create menu id
        mobj = self.env['ir.ui.menu']
        menu_id = mobj.sudo().create({'name': vals['name'],
                                      'parent_id': menu_parent,
                                      'sequence': 100,
                                      'icon_file': '/epps_design/static/src/img/project-icon.png',
                                      })
        # TODO: Update ir_ui_menu set icon = '/epps_design/static/src/img/project-icon.png'
        #        where id= %menu_id

        # write menu_id on project for performance on unlink
        vals['menu_id'] = menu_id.id
        res = super(Project, self).create(vals)

        # get action and copy action with new res_id
        ref = self.env['ir.model.data'].get_object_reference('epps_project',
                                                             'epps_project_edit_act')
        if ref:
            actions_obj = self.pool.get('ir.actions.act_window')
            # NEW API - COPY DOESN'T WORK FOR SOME REASON
            #new_action = actions_obj.sudo().copy(ref[1], default={'res_id': res.id,})
            new_action = actions_obj.copy(self._cr, SUPERUSER_ID, ref[1],
                                          default={'res_id': res.id,
                                                   'name': vals['name'], },
                                          context=self._context)

        # update menu item with action now that we have action
        menu_id.sudo().write(
            {'action': 'ir.actions.act_window,' + str(new_action)})

        # Get users for to add to group
        user_ids = []
        project_manager_id = False
        if vals.get('user_id', False):
            user_ids.extend([vals['user_id']])
            project_manager_id = vals['user_id']
        if vals.get('members', False):
            for member in vals['members']:
                user_ids.extend(member[2])
            # Automaticly add all team members of project to message followers
            res.message_subscribe_users(user_ids=user_ids,
                                        subtype_ids=None)
       
        # get unique user list (constraint on relation table
        # res_groups_users_rel_gid_uid_key)
        unique_user_ids = set(user_ids)
        
        # Auto add project to projects_to_follow on user
        user_obj = self.env['res.users']
        users = user_obj.browse(list(unique_user_ids))

        for user in users:
            user.sudo().write({'projects_to_follow': [(4, [res.id])]})
        # Create new group add users and assign it to menu
        gobj = self.env['res.groups']
        user_group = self.env['ir.model.data'].get_object_reference('epps_project',
                                                                    'group_epps_project_user')
        user_group = user_group and [user_group[1]] or []
        manager_group = self.env['ir.model.data'].get_object_reference('epps_project',
                                                                       'group_epps_project_manager')
        manager_group = manager_group and [manager_group[1]] or False
        projects_category = self.env['ir.model.data'].sudo().xmlid_to_object(
            'base.module_category_project_per_user')
        group_id = gobj.sudo().create({'name': vals['name'],
                                       'menu_access': [(6, 0, [menu_id.id])],
                                       'implied_ids': [(6, 0, user_group)],
                                       'users': [(6, 0, list(unique_user_ids))],
                                       'category_id': projects_category.id,
                                       'group_admin_id': project_manager_id,
                                       })

        if vals.get('privacy_visibility', False):
            public_project_group = self.env.ref("epps_user.group_epps_public_project_user") or False
            if public_project_group and vals['privacy_visibility'] == 'public':
                public_project_group.sudo().write({'menu_access': [(4, [menu_id.id])]})

        manager_group = self.env['res.groups'].browse(manager_group)
        manager_group.sudo().write({'implied_ids': [(4, group_id.id)]})
        # write group_id on project so we don't have to do a lot of searching
        # on unlink
        res.write({'group_id': group_id.id})

        # create a directory for the project
        if res:
            project_document_directory = self.env['document.directory'].get_proj_root(res.id)
        # Refresh menu. Same logic as in module update. Not needed anymore?
        # api.Environment.reset()
        #modules.registry.RegistryManager.new(self._cr.dbname, update_module=True)

        users_on_project = self._get_member_names(users)
        res.message_post(
            body="<b>Project Created:</b> %s" % (users_on_project),
            subtype='project.project_created')
        return res

    @api.multi
    def write(self, vals):
        if vals.get('name', False):
            project_name = self.search([('name', '=', vals['name']), ('id', '!=', self.id)], limit=1)
            if project_name:
                if vals['name'] == project_name[0].name:
                    raise Warning(_("Please pick another name, project with that name already exists."))

            document_directory_obj = self.env['document.directory'].search([('ressource_id', '=', self.id)], limit=1)
            if document_directory_obj:
                document_directory_obj[0].sudo().write({'name': vals['name']})
            else:
                raise Warning(_("Project directory does not exist."))
            self.menu_id.sudo().write({'name': vals['name']})
            self.group_id.sudo().write({'name': vals['name']})

        if vals.get('privacy_visibility', False):
            public_project_group = self.env.ref("epps_user.group_epps_public_project_user") or False
            if public_project_group and vals['privacy_visibility'] == 'public':
                public_project_group.sudo().write({'menu_access': [(4, [self.menu_id.id])]})
            else:
                user_list = []
                user_list = self.env['res.users'].sudo().search([])
                public_project_group.sudo().write({'menu_access': [(3, self.menu_id.id)]})
                #We need to remove all the users folowing this project except project manager and team members.
                for u in user_list:
                    if u.id not in self.members._ids and u.id != self.id:
                        u.sudo().write({'projects_to_follow': [(3, self.id)]})

        res = super(Project, self).write(vals)
        return res

    @api.multi
    def copy(self, default=None):
        if default is None:
            default = {}

        new_project_name = self.name
        _get_project_name = self.env['project.project'].search([('name', '=', self.name)], limit=1)

        if _get_project_name:
            sufix_num = 1
            while self.env['project.project'].search(
                    [('name', '=', new_project_name + "(" + _("copy") + str(sufix_num) + ")")], limit=1):
                sufix_num += 1
                if sufix_num > 99999:
                    raise Warning(_("Please consider another name for the project."))
            new_project_name = new_project_name + "(" + _("copy") + str(sufix_num) + ")"
        default['name'] = new_project_name
        #remove all members from the project
        default['members'] = None
        res = super(Project, self).copy(default)

        return res

    @api.multi
    def unlink(self):
        for project in self:
            if project.state != 'draft':
                raise Warning(
                    _("You can't delete project that is not in draft "
                      "state. Order: %s" % project.name))
            elif project.is_company_rules:
                return False
            elif project.is_my_files:
                return False
            elif project.is_repository:
                return False
            elif project.is_conbase:
                return False
            else:
                # unlink records that we created upon create
                actions_obj = self.pool.get('ir.actions.act_window')
                action_to_delete = actions_obj.search(
                    self._cr, self._uid, [('res_id', '=', project.id)])
                actions_obj.unlink(self._cr, SUPERUSER_ID,
                                   action_to_delete, context=self._context)

                # unlink directory
                directory_obj = self.pool.get('document.directory')
                directory_to_delete = directory_obj.search(
                    self._cr, self._uid, [('ressource_id', '=', project.id)])
                directory_obj.unlink(self._cr, SUPERUSER_ID,
                                   directory_to_delete, context=self._context)

                project.menu_id.sudo().unlink()
                project.group_id.sudo().unlink()
        res = super(Project, self).unlink()
        return res

    def _get_visibility_selection(self, cr, uid, context=None):
        """ Overriden in portal_project to offer more options """
        return [('public', _('Public:\n everyone in this network')),
                ('employees', _('Members Only:\n only project members see the content')),
                #('followers', _('Followers Only: employees see only the followed tasks or issues')),
                ]

    """
    BUTTONS
    """
    @api.multi
    def create_new(self):
        return {
            'name': _('New Project'),
            'context': self._context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'project.project',
            #'views': [(self.id,'form')],
            'type': 'ir.actions.act_window',
            'target': 'current',
        }

    @api.multi
    def save_current(self):
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
            'params': {
                'menu_id': self.menu_id.id
            },
        }

    @api.multi
    def delete_current(self):
        if self.user_id.id != self._uid and self.user_id.id != SUPERUSER_ID and not self.user_has_groups('epps_user.group_customer_administrator'):
            raise Warning(_(''),_('You are not allowed to do this.'))
            return False
        res = self.unlink()
        return res

    @api.multi
    def edit_current(self):
        if self.user_id.id != self._uid and self.user_id.id != SUPERUSER_ID and not self.user_has_groups('epps_user.group_customer_administrator'):
            raise Warning(_(''), _('You are not allowed to do this.'))
            return False
        view = self.env.ref('epps_project.epps_create_project_form')
        return {
            'name': _('Project'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'project.project',
            'view_id': view.id,
            'type': 'ir.actions.act_window',
            'target': 'inline',  # 'new',
            'res_id': self.id,
        }

    @api.multi
    def duplicate_current(self):
        if self.user_id.id != self._uid and self.user_id.id != SUPERUSER_ID and not self.user_has_groups('epps_user.group_customer_administrator'):
            raise Warning(_(''), _('You are not allowed to do this.'))
            return False
        res = self.copy()
        return res

    @api.multi
    def close_current(self):
        return True

    @api.multi
    def archive_current(self):
        if self.user_id.id != self._uid and self.user_id.id != SUPERUSER_ID and not self.user_has_groups('epps_user.group_customer_administrator'):
            raise Warning(_(''), _('You are not allowed to do this.'))
            return False
        self.active = False
        archive_menu = self.env['ir.model.data'].get_object_reference('epps_project',
                                                                      'epps_menu_project_archive')
        archive_menu = archive_menu and archive_menu[1] or False
        menuitem = self.menu_id
        menuitem.sudo().write({'parent_id': archive_menu, })
        reload_menu = self.env['ir.model.data'].get_object_reference('base',
                                                                     'epps_menu_main_pm')
        reload_menu = reload_menu and reload_menu[1] or False
        res = {
            'type': 'ir.actions.client',
            'tag': 'reload',
            'params': {
                'menu_id': reload_menu
            },
        }
        return res

    @api.multi
    def unarchive_current(self):
        if self.user_id.id != self._uid and self.user_id.id != SUPERUSER_ID and not self.user_has_groups('epps_user.group_customer_administrator'):
            raise Warning(_(''), _('You are not allowed to do this.'))
            return False
        self.active = True
        project_menu = self.env['ir.model.data'].get_object_reference('epps_project',
                                                                      'epps_menu_project_management')
        project_menu = project_menu and project_menu[1] or False
        menuitem = self.menu_id
        menuitem.sudo().write({'parent_id': project_menu, })
        reload_menu = self.env['ir.model.data'].get_object_reference('base',
                                                                     'epps_menu_main_pm')
        reload_menu = reload_menu and reload_menu[1] or False
        res = {
            'type': 'ir.actions.client',
            'tag': 'reload',
            'params': {
                'menu_id': reload_menu
            },
        }
        return res

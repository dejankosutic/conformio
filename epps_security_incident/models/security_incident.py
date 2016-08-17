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


class SecurityIncident(models.Model):
    _name = 'security.incident.conbase'

    name = fields.Char('name')
    incident_ids = fields.One2many('security.incident.conitem', 'incident_id', string='Incidents')
    pad_ids = fields.One2many('security.incident.conbase.pad', 'security_incident_id', string='Notes')
    # Uses a project in the background to attach files and discussions
    project_id = fields.Many2one('project.project')
    messages_4_recenttasks = fields.One2many(related='project_id.messages_4_recenttasks')
    messages_4_recentdiscussions = fields.One2many(related='project_id.messages_4_recentdiscussions')
    messages_4_recentfiles = fields.One2many(related='project_id.messages_4_recentfiles')
    messages_4_discussions = fields.One2many(related='project_id.messages_4_discussions')
    message_ids = fields.One2many(related='project_id.message_ids')
    
    @api.model
    def create(self, vals):
        name = vals.get('name', False)
        return super(SecurityIncident, self).create(vals)


class IncidentType(models.Model):
    _name = 'incident.type'

    name = fields.Char('name')


class IncidentStatus(models.Model):
    _name = 'incident.status'

    name = fields.Char('name')
    done = fields.Boolean()
    #color = fields.Char('color')


class IncidentCorrectiveActions(models.Model):
    _name='incident.corrective.actions'

    name = fields.Char('name')


class SecurityIncidentItem(models.Model):

    _name = 'security.incident.conitem'


    name = fields.Char('name')
    status = fields.Many2one('incident.status', 
            'Document status',
            select=True)
    date = fields.Date('Date nad time of the incident')
    person = fields.Char('Person who reported the incident', default="")
    description = fields.Text('Description', default='')
    cost = fields.Char('Cost', default="")
    corrective_actions = fields.Many2many('incident.corrective.actions')
    related_risks = fields.Char('Related risks')
    assigned_user_id = fields.Many2one('res.users', 'Assigned to')
    task_ids = fields.One2many('project.task', 'security_incident_id', string='Tasks')
    incident_id = fields.Many2one('security.incident.conbase', string='Security incident base')
    is_assigned = fields.Char(compute="_is_assigned")
    incident_type = fields.Many2one('incident.type', string='Incident type')
    done = fields.Boolean(related='status.done')
    tags = fields.Char('Tags')
    task_4_messages = fields.Many2one('project.task')
    # TODO : files

    @api.model
    def create(self, vals):
        rec = super(SecurityIncidentItem, self).create(vals)
        rec.incident_id = 1
        rec.task_4_messages = self.env['project.task'].create({'name': rec.name, 'project_id': rec.incident_id.project_id.id})
        return rec


    @api.depends('assigned_user_id')
    def _is_assigned(self):
        for record in self:
            record.is_assigned = "Assigned" if record.assigned_user_id else "Unassigned"

    @api.multi
    def delete_item_recoursivly(self, removed_tasks):
        sub_tasks = self.env['project.task'].search([('security_incident_id', '=', self.id)])
        if sub_tasks:
            for _task in sub_tasks:
                removed_tasks = _task.delete_task_recoursivly(removed_tasks)
            self.unlink()
            removed_tasks.append(self.id)
        else:
            self.unlink()
            removed_tasks.append(self.id)
        return removed_tasks


class ProjectTask(models.Model):
    _inherit = 'project.task'

    security_incident_id = fields.Many2one('security.incident.conitem', 'security_incident_id')


class SecurityIncidentPad(models.Model):
    _name = 'security.incident.conbase.pad'
    _inherit = ['pad.common']

    security_incident_id = fields.Many2one('security.incident.conbase', 'Security incident base')

    name = fields.Char(string='Note name')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting_approval', 'Waiting for approval'),
        ('approved', 'Approved'),
        ('canceled', 'Cancelled'),
    ], string='State', default='draft', track_visibility='onchange')
    author_user_id = fields.Many2one('res.users', 'Author')
    approve_user_id = fields.Many2one('res.users', 'Approver')
    note = fields.Char('Note')
    note_pad = fields.Char('Note', pad_content_field='note')

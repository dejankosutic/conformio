# -*- coding: utf-8 -*-
##############################################################################
# This software is © copyright 2016 EPPS Services Ltd and licensed under the
# GNU Affero General Public License, version 3.0 as published by the Free
# Software Foundation.
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################

from openerp import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class DWAFields(models.Model):
    _name = 'dwa.fields'
    _description = 'DWA Fields'
    _order = 'sequence,id'

    sequence = fields.Integer(string="Sequence", default=1)
    name = fields.Char(string="Name", required=True, translate=True)
    value = fields.Char(string="Value", required=True, translate=True)
    deletable = fields.Integer(string="Deletable", required=False, readonly=True, default=1)
    ir_att_id = fields.Integer(string="Attachment ID", required=False, readonly=True, default=0)
    logo = fields.Binary('Logo')

    _defaults = {
        'sequence': 1,
    }

    _sql_constraints = [
        ('unique_field_name', 'UNIQUE (name)', 'Field name must be unique!'),
        ('positive_sequence', 'CHECK(sequence >= 0)',
         'Sequence number MUST be a natural')
    ]

    @api.multi
    def write(self, vals):
        print "A"
        return super(DWAFields, self).write(vals)
    

class Project(models.Model):
    _name = 'project.project'
    _inherit = ['project.project']

    is_company_rules = fields.Boolean(
        string='Company rules project',
        default=False, readonly=True, select=True
    )

    is_my_files = fields.Boolean(
        string='My files project',
        default=False, readonly=True, select=True
    )

    is_repository = fields.Boolean(
        string='Repository project',
        default=False, readonly=True, select=True
    )

    is_conbase = fields.Boolean(
        string='conbase project',
        default=False, readonly=True, select=True
    )

    _defaults = {
        'is_company_rules': False,
        'is_my_files': False,
        'is_repository': False,
        'is_conbase': False
    }

    def _auto_init(self, cr, context=None):
        super(Project, self)._auto_init(cr, context)
        # cr.execute(
        #     "UPDATE ir_actions_todo  SET state = 'done' WHERE state = 'open'")
        cr.execute(
            'UPDATE project_project  SET is_company_rules = false WHERE is_company_rules IS NULL')
        cr.execute(
            'UPDATE project_project  SET is_my_files = false WHERE is_my_files IS NULL')
        cr.execute(
            'UPDATE project_project  SET is_repository = false WHERE is_repository IS NULL')
        cr.execute(
            'UPDATE project_project  SET is_conbase = false WHERE is_conbase IS NULL')
        cr.execute(
            'ALTER TABLE project_project  ALTER COLUMN is_company_rules SET DEFAULT false')
        cr.execute(
            'ALTER TABLE project_project  ALTER COLUMN is_my_files SET DEFAULT false')
        cr.execute(
            'ALTER TABLE project_project  ALTER COLUMN is_repository SET DEFAULT false')
        cr.execute(
            'ALTER TABLE project_project  ALTER COLUMN is_conbase SET DEFAULT false')


    dwa_fields_ids = fields.One2many(
        'dwa.fields',
        compute='_get_dwa_fields',
        string='Automation'
    )

    @api.one
    def _get_dwa_fields(self):
        if self.is_company_rules: # only
            self.finished_task_ids = self.env['dwa.fields'].browse()
        #else:
        #    self.finished_task_ids = self.env['dwa.fields'].browse([-1])

# -*- coding: utf-8 -*-
##############################################################################
# This software is © copyright 2016 EPPS Services Ltd and licensed under the
# GNU Affero General Public License, version 3.0 as published by the Free
# Software Foundation.
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################

from openerp import models, fields


class EppsHrJob(models.Model):
    _name = 'epps.hr.job'
    name = fields.Char('Job Name',
                       required=True,
                       select=True,
                       translate=True)


class EppsHrDepartment(models.Model):
    _name = 'epps.hr.department'
    name = fields.Char('Department Name',
                       required=True,
                       select=True,
                       translate=True)


class ResUsers(models.Model):
    _inherit = 'res.users'

    job_id = fields.Many2one('epps.hr.job', string="Job Title",)
    department_id = fields.Many2one('epps.hr.department', string="Department",)

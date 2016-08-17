# -*- coding: utf-8 -*-
##############################################################################
# This software is © copyright 2016 EPPS Services Ltd and licensed under the
# GNU Affero General Public License, version 3.0 as published by the Free
# Software Foundation.
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################

from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning


class DocumentFileStatus(models.Model):
    """Document status"""
    _name = 'document.file.status'
    _description = 'Document status'
    _order = 'sequence,id'

    name = fields.Char(string="Name", required=True, translate=True)
    sequence = fields.Integer(string="Sequence")
    state = fields.Selection([('new', 'New'),
                              ('in_progress', 'In progress'),
                              ('done', 'Done')],
                              'State')
    permanent = fields.Boolean(string="Permanent");

    _defaults = {
        'sequence': 1,
        'state': 'in_progress',
        'permanent': False 
    }

    _sql_constraints = [
        ('positive_sequence', 'CHECK(sequence > 0 and sequence < 100)',
         _('Sequence number MUST be a natural number below 100.'))
    ]

    @api.multi
    def write(self, vals=None):
        if self.permanent == True:
            raise Warning(_("Sorry you can not change/remove this document status."))
        else:
            return super(DocumentFileStatus, self).write(vals)

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.permanent == True:
                raise Warning(_("Sorry you can not change/remove this document status."))
            else:
                return super(DocumentFileStatus, self).unlink()
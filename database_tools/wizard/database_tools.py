# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################

from openerp import models, fields


class DbDatabaseToolsWizard(models.TransientModel):
    _name = 'db.database.tools.wizard'
    # TODO borrar, lo dejamos para que el modulo sea desinstalable

    name = fields.Char('New Database Name', size=64, required=True)
    action_type = fields.Char('Action Type', required=True)
    backups_enable = fields.Boolean('Backups Enable on new DB?')

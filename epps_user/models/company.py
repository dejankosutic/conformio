# -*- coding: utf-8 -*-
##############################################################################
# This software is © copyright 2016 EPPS Services Ltd and licensed under the
# GNU Affero General Public License, version 3.0 as published by the Free
# Software Foundation.
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################

from openerp import models, fields, api


class ResCompany(models.Model):

    _inherit = 'res.company'

    client_role = fields.Selection([('client', 'Client'),
                                   ('reseller', 'Reseller'),
                                   ('reseller_client', 'Reseller-Client')],
                                   'Client role',
                                   default='client'
                                   )

    max_number_of_users = fields.Integer(
        string='Max',
        help='Maximum number of users',
        default=5)
    number_of_users = fields.Integer(
        string='Number of users',
        help='Number of active users.',
        compute='_get_number_of_users'
    )
    remaining_users = fields.Integer(
        string='Remaining users',
        help='Number of remaining users.',
        compute='_get_number_of_users',
    )
    max_space_gb = fields.Integer(
        string='Max. space (GB)',
        help='Maximum disk space in GB.',
        default=5)

    def _get_number_of_users(self):
        self.env.cr.execute("""
            SELECT count(*)
              FROM res_users
             WHERE id !=1
               AND share = false
               AND active = true""")
        number_of_current_users = self.env.cr.fetchone()
        if number_of_current_users:
            self.number_of_users = number_of_current_users[0]
            self.remaining_users = \
                self.max_number_of_users - self.number_of_users

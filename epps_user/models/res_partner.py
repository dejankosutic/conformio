# -*- coding: utf-8 -*-
##############################################################################
# This software is © copyright 2016 EPPS Services Ltd and licensed under the
# GNU Affero General Public License, version 3.0 as published by the Free
# Software Foundation.
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################

from openerp import models, fields, api, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Inverts the place of lastname and firstname in name
    @api.model
    def _get_computed_name(self, lastname, firstname):
        super(ResPartner, self)._get_computed_name(lastname, firstname)
        return u" ".join((p for p in (firstname, lastname) if p))
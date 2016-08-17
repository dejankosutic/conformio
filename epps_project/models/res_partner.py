# -*- coding: utf-8 -*-
##############################################################################
# This software is © copyright 2016 EPPS Services Ltd and licensed under the
# GNU Affero General Public License, version 3.0 as published by the Free
# Software Foundation.
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################

import logging
from openerp import api, fields, models

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _auto_init(self, cr, context=None):
        cr.execute(
            "UPDATE res_partner "
            "   SET firstname = name"
            " WHERE firstname IS NULL"
        )
        return super(ResPartner, self)._auto_init(cr, context)

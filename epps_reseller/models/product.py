# -*- coding: utf-8 -*-
##############################################################################
# This software is © copyright 2016 EPPS Services Ltd and licensed under the
# GNU Affero General Public License, version 3.0 as published by the Free
# Software Foundation.
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################

from openerp import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    material_type = fields.Selection(
        (('L', 'L - Conformio plan'),
         ('DT', 'DT - Documentation Toolkit'),
         ('ID', 'ID - Individual Document'),
         ('VT', 'VT - Video Tutorial'),
         ('WR', 'WR - Webinar Recording'),
         ('LW', 'LW - Live Webinar'),
         ('SP', 'SP - Subscription Plan'),
         ('PB', 'PB - Paper Book'),
         ('EB', 'EB - eBook'),
         ('LS', 'LS - Live service'),
         ('AR', 'AR - Article'),
         ('LT', 'LT - List of tasks'),
         ('FD', 'FD - Free downloads'),
         ('WD', 'WD - Web document'),
         ('QU', 'QU - Questionnaire'),
         ('PP', "PP - PDF Preview's Toolkit"),
         ('FP', 'FP - Free Preview Toolkit'),
         ('FT', 'FT - Free Template'),
        ),
        'Material Type')
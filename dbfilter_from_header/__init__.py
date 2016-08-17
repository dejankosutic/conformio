# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    This module copyright (C) 2013 Therp BV (<http://therp.nl>).
#    This module copyright (C) 2014 ACSONE SA/NV (<http://acsone.eu>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import re
from openerp import http
import werkzeug.utils
import werkzeug.wrappers
import logging
import openerp
import openerp.http
from openerp.addons.web.controllers.main import Database
from openerp.http import request

_logger = logging.getLogger(__name__)


db_filter_org = http.db_filter


def db_filter(dbs, httprequest=None):
    dbs = db_filter_org(dbs, httprequest)
    httprequest = httprequest or http.request.httprequest
    db_filter_hdr_odoo = httprequest.environ.get('HTTP_X_ODOO_DBFILTER')
    db_filter_hdr_openerp = httprequest.environ.get('HTTP_X_OPENERP_DBFILTER')



    if db_filter_hdr_odoo and db_filter_hdr_openerp:
        raise RuntimeError("x-odoo-dbfilter and x-openerp-dbfiter "
                           "are both set")
    db_filter_hdr = db_filter_hdr_odoo or db_filter_hdr_openerp
    if db_filter_hdr:
        dbs = [db for db in dbs if db_filter_hdr == db]

        if len(dbs) == 0:
            dbs = [db for db in dbs if re.match(db_filter_hdr, db)]

    return dbs

http.db_filter = db_filter

from openerp.addons.web.controllers.main import Database

_logger = logging.getLogger(__name__)


class Database2(Database):
    @http.route()
    def manager(self, **kw):
        url = "http://advisera.com/conformio/noaccount/"
        return werkzeug.utils.redirect(url)

    @http.route()
    def selector(self, **kw):
        url = "http://advisera.com/conformio/noaccount/"
        return werkzeug.utils.redirect(url)
#
# @http.route('/web/database/selector', type='http', auth="none")
# def selector2(self, **kw):
#     url = "http://advisera.com/conformio/noaccount/"
#     return werkzeug.utils.redirect(url)
#
#
# Database.selector = selector2
#
#
# @http.route('/web/database/manager', type='http', auth="none")
# def manager2(self, **kw):
#     url = "http://advisera.com/conformio/noaccount/"
#     return werkzeug.utils.redirect(url)
#
#
# Database.manager = manager2

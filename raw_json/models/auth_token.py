# -*- coding: utf-8 -*-
##############################################################################
# This software is © copyright 2016 EPPS Services Ltd and licensed under the
# GNU Affero General Public License, version 3.0 as published by the Free
# Software Foundation.
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################

from datetime import datetime, timedelta
from openerp.osv import osv, fields
from openerp.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT, ustr
import uuid


def random_token():
    return uuid.uuid4().hex
    # the token has an entropy of about 120 bits (6 bits/char * 20 chars)
    # chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
    # return ''.join(random.SystemRandom().choice(chars) for i in xrange(20))


def now(**kwargs):
    dt = datetime.now() + timedelta(**kwargs)
    return dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT)


class ResUsers(osv.Model):
    _inherit = 'res.users'

    def _get_auth_valid(self, cr, uid, ids, name, arg, context=None):
        dt = now()
        res = {}
        for user in self.browse(cr, uid, ids, context):
            res[user.id] = bool(user.auth_token) and \
                (not user.auth_expiration or dt <= user.auth_expiration)
        return res

    _columns = {
        'auth_token': fields.char('Signup Token', copy=False),
        'auth_expiration': fields.datetime('Signup Expiration', copy=False),
        'auth_valid': fields.function(_get_auth_valid, type='boolean', string='Signup Token is Valid'),
    }

    def get_auth_token(self, cr, uid, ids, expiration=False, context=None):
        for user in self.browse(cr, uid, ids, context):
            if expiration or not user.auth_valid:
                token = random_token()
                while self._auth_retrieve_user(cr, uid, token, context=context):
                    token = random_token()
                user.write(
                    {'auth_token': token, 'auth_expiration': expiration})
            else:
                return user.auth_token
        return token

    def _auth_retrieve_user(self, cr, uid, token,
                            check_validity=False, context=None):
        user_ids = self.search(
            cr, uid, [('auth_token', '=', token)], context=context)
        if not user_ids:
            return False
        user = self.browse(cr, uid, user_ids[0], context)
        if check_validity and not user.auth_valid:
            return False
        return user

# -*- coding: utf-8 -*-
##############################################################################
# This software is © copyright 2016 EPPS Services Ltd and licensed under the
# GNU Affero General Public License, version 3.0 as published by the Free
# Software Foundation.
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################

import openerp
from openerp.service import common, security
from openerp import models, fields, api, _, SUPERUSER_ID


class EppsUserLog(models.AbstractModel):
    '''When you use monkey patching, the code is executed when the module
    is in the addons_path of the OpenERP server, even is the module is not
    installed ! In order to avoid the side-effects it can create,
    we create an AbstractModel inside the module and we test the
    availability of this Model in the code of the monkey patching below.
    At Akretion, we call this the "Guewen trick", in reference
    to a trick used by Guewen Baconnier in the "connector" module.
    '''
    _name = "epps_user_log.installed"


orig_exp_login = common.exp_login


def exp_login(db, login, password):
    res = orig_exp_login(db, login, password)
    is_installed = openerp.registry(db).get('epps_user_log.installed', False)
    if is_installed and res:
        user_id = res
        user_log_present = openerp.registry(db).get('user.log', False)
        if user_log_present:
            user_log = openerp.registry(db)['user.log']
            user_log._create_new_log(db, user_id)
    return res or False

common.exp_login = exp_login

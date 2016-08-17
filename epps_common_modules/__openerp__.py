# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 Slobodni Programi d.o.o. (<http://slobodni-programi.hr>).
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

{
    'name': 'Epps common modules collection',
    'version': '8.0.1.0.0',
    'author': 'Slobodni-programi d.o.o.',
    'maintainer': 'False',
    'website': 'False',
    'license': 'AGPL-3',
    # any module necessary for this one to work correctly
    'depends': [
        'inactive_session_timeout',
        'user_avatar_initials',
        'web_list_button_icon',
        'web_radio_button',
        'web_group_expand',
        'document',
        'epps_mail',
        'epps_hr',
        'epps_company_rules',
        'epps_project',
        'epps_design',
        'document_webdav_fast',
        'raw_json',
        'epps_account_settings',
    ],
    'external_dependencies': {
        'python': [],
    },

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml # noqa
    # for the full list
    'category': 'Others',
    'summary': 'Epps common modules collection install via dependencies',

    # always loaded
    'data': [
    ],
    # only loaded in demonstration mode
    'demo': [
    ],

    # used for Javascript Web CLient Testing with QUnit / PhantomJS
    # https://www.odoo.com/documentation/8.0/reference/javascript.html#testing-in-odoo-web-client  # noqa
    'js': [],
    'css': [],
    'qweb': [],

    'installable': True,
    # Install this module automatically if all dependency have been previously
    # and independently installed.  Used for synergetic or glue modules.
    'auto_install': False,
    'application': False,
}

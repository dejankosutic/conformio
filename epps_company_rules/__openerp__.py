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
    'name': 'Epps company rules',
    'version': '8.0.1.0.0',
    'author': 'Decodio',
    'category': 'EPPS Modules',
    'summary': 'Epps company rules',
    'website': 'http://slobodni-programi.com',
    'license': 'AGPL-3',
    'depends': ['epps_design',
               ],
    'data': ['wizard/update_logo_name.xml',
             'views/company_rules_project.xml',
             'views/company_rules_menu.xml',
             'views/company_rules_includes.xml',
             'views/menu_icons.xml'
             ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'auto_install': False,
    'application': False,
}

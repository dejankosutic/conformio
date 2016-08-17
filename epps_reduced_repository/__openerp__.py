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
    'name': 'Epps reduced repository',
    'version': '0.1',
    'author': 'Decodio',
    'summary': '',
    'category': 'EPPS Modules',
    'website': 'http://slobodni-programi.com',
    'license': 'AGPL-3',
    'depends': ['base',
                'epps_design',
                'epps_project'
                ],
    'demo': [],
    'data': ['static/src/xml/design.xml',
             'views/epps_repository_view.xml'],
    'qweb': ['static/src/xml/epps_reduced_repository.xml'],
    'auto_install': False,
    'application': False,
    'installable': True,
}

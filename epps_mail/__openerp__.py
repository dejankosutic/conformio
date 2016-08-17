# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2014 Decodio / Slobodni Programi d.o.o. (<http://slobodni-programi.hr>).
#    Author: Goran Kliska
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
    'name': 'Epps mail',
    'version': '8.14.11.0',
    'category': 'Base/Borg',
    'complexity': "normal",
    "depends": ['mail',
                'auth_signup'
                ],
    'author': 'Decodio - Slobodni programi d.o.o.',
    'website': 'http://slobodni-programi.com',
    'license': 'AGPL-3',
    'data': [
             'wizard/mail_compose_message_view.xml',
             'views/mail_template.xml',
             'data/epps_mail.xml',
            ],
    'demo_xml': [],
    'images': [],
    'qweb': [
             'static/src/xml/epps_mail.xml',
            ],
    'auto_install': False,
    'application': False,
    'installable' : True,
}

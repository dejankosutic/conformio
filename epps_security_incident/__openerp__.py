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
    'name' : 'EPPS Security incident',
    'version' : '1.0',
    'author' : 'Info3',
    'summary': 'EPPS Security incident',
    'description': """
                   """,
    'category': 'EPPS Modules',
    'website' : 'http://info3.hr',
    'depends' : [
        'base',
        'epps_project',
        ],
    'demo' : [],
    'data' : [
        'views/security_incident_records.xml',
        'views/security_incident_view.xml',
        'views/security_incident_settings.xml',
        #'security/ir.model.access.csv',
    ],
    'qweb': [
            ],
    'auto_install': False,
    'application': False,
    'installable': True,
}

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
    'name': 'EPPS Project',
    'version': '1.0',
    'author': 'Decodio',
    'summary': 'EPPS Project',
    'category': 'EPPS Modules',
    'website': 'http://slobodni-programi.com',
    'license': 'AGPL-3',
    'depends': ['base',
                'epps_user',
                'mail',
                'project',
                'pad',
                'pad_project',
                'document',
                'web_radio_button',
                'web_list_button_icon',
                'web_ir_actions_act_window_page',
                'web_ckeditor4',
                'epps_hr',
                ],
    'demo': [],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/delete_subtypes.xml',
        'data/document_status_data.xml',
        'data/repository_project_data.xml',
        'data/mail_templates.xml',
        'data/like_mail_template.xml',
        'data/document_change_mail_template.xml',
        'data/new_file_template_data.xml',
        'data/document.xml',
        'views/mail_message_subtype.xml',
        'views/epps_project_css.xml',
        'views/project_view.xml',
        'views/mail_thread_view.xml',
        'views/user_view.xml',
        'views/hide_menus.xml',
        'views/document_status_view.xml',
        'views/epps_repository_view.xml',
        'views/epps_setting_menu_view.xml',
        'views/epps_repository_menu_view.xml',
        'views/message_tags_view.xml',
        'views/ir_attachment_view.xml',
        'views/res_users_view.xml',
    ],
    'qweb': [
        'static/src/xml/mail.xml',
    ],
    'auto_install': False,
    'application': False,
    'installable': True,
}

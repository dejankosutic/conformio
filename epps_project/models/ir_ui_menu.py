# -*- coding: utf-8 -*-
##############################################################################
# This software is © copyright 2016 EPPS Services Ltd and licensed under the
# GNU Affero General Public License, version 3.0 as published by the Free
# Software Foundation.
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################

import operator


from openerp.osv import fields, osv
from openerp import api, tools
from openerp.tools.safe_eval import safe_eval as eval
from openerp.tools.translate import _


class IrUiMenu(osv.osv):
    _name = 'ir.ui.menu'
    _inherit = ['ir.ui.menu']
    _parent_order = 'sequence'

    """ Field creation moved to epps_project module
    _columns = {
        'icon_file' : fields.char('Icon File'),
    }
    """

    #icon = fields.Char('icon', default='/epps_design/static/src/img/checkbox-checked.png')
    @api.cr_uid_context
    @tools.ormcache_context(accepted_keys=('lang',))
    def load_menus_root(self, cr, uid, context=None):
        fields = ['name', 'sequence', 'parent_id', 'action', 'icon_file']
        menu_root_ids = self.get_user_roots(cr, uid, context=context)
        menu_roots = self.read(cr, uid, menu_root_ids,
                               fields, context=context) if menu_root_ids else []
        return {
            'id': False,
            'name': 'root',
            'parent_id': [-1, ''],
            'children': menu_roots,
            'icon_file': '/epps_design/static/src/img/checkbox-checked.png',
            'all_menu_ids': menu_root_ids,
        }

    @api.cr_uid_context
    @tools.ormcache_context(accepted_keys=('lang',))
    def load_menus(self, cr, uid, context=None):
        """ Loads all menu items (all applications and their sub-menus).

        :return: the menu root
        :rtype: dict('children': menu_nodes)
        """
        fields = ['name', 'sequence', 'parent_id', 'action', 'icon_file']
        menu_root_ids = self.get_user_roots(cr, uid, context=context)
        menu_roots = self.read(cr, uid, menu_root_ids,
                               fields, context=context) if menu_root_ids else []
        menu_root = {
            'id': False,
            'name': 'root',
            'parent_id': [-1, ''],
            'children': menu_roots,
            'icon_file': '/epps_design/static/src/img/checkbox-checked.png',
            'all_menu_ids': menu_root_ids,
        }
        if not menu_roots:
            return menu_root

        # menus are loaded fully unlike a regular tree view, cause there are a
        # limited number of items (752 when all 6.1 addons are installed)
        menu_ids = self.search(
            cr, uid, [('id', 'child_of', menu_root_ids)], 0, False, False, context=context)
        menu_items = self.read(cr, uid, menu_ids, fields, context=context)
        # adds roots at the end of the sequence, so that they will overwrite
        # equivalent menu items from full menu read when put into id:item
        # mapping, resulting in children being correctly set on the roots.
        menu_items.extend(menu_roots)
        menu_root['all_menu_ids'] = menu_ids  # includes menu_root_ids!

        # make a tree using parent_id
        menu_items_map = dict(
            (menu_item["id"], menu_item) for menu_item in menu_items)
        for menu_item in menu_items:
            if menu_item['parent_id']:
                parent = menu_item['parent_id'][0]
            else:
                parent = False
            if parent in menu_items_map:
                menu_items_map[parent].setdefault(
                    'children', []).append(menu_item)

        # sort by sequence a tree using parent_id
        for menu_item in menu_items:
            menu_item.setdefault('children', []).sort(
                key=operator.itemgetter('sequence'))

        return menu_root

/*!
 * This software is © copyright 2016 EPPS Services Ltd and licensed under the
 * GNU Affero General Public License, version 3.0 as published by the Free
 * Software Foundation.
 */
openerp.epps_user = function(instance) {
    var _t = instance.web._t;
    var QWeb = instance.web.qweb;
    var SUPERUSER_ID = 1;
    
    instance.web.UserMenu = instance.web.UserMenu.extend({
        /*
         * Open Change Password Modal Dialog
         */
        on_menu_password: function() {
            var self = this;
            var action = {type:   'ir.actions.client',
                          tag:    'change_password',
                          target: 'new',
                         };
            instance.client.action_manager.do_action(action);
            },
        /*
         * Open Notification Settings
         */
        on_menu_notifications: function() {
            this.rpc("/web/action/load", {"action_id": "epps_user.action_user_notifications_my",}).done(function(action) {
                 action.res_id = instance.session.uid;
                 instance.client.action_manager.do_action(action);
            });
         },
         /*
          * Open Epps About Dialog
          */
        on_menu_about_epps: function() {
            var self = this;
            self.rpc("/web/webclient/version_info", {}).done(function(res) {
                model =  new instance.web.Model('res.users');
                model.call('get_reseller_logo_id',[], { context: new instance.web.CompoundContext() }).then(function(result) {

                    var epps_reseller_logo_id = false;
                    var is_number = !isNaN(result);
                    if(result && result != 'undefined' && result != 'false' && is_number) {
                        epps_reseller_logo_id = result;
                    }
                    else {
                        epps_reseller_logo_id = false;
                    }

                    var $help = $(QWeb.render("UserMenu.about_epps", {version_info: res, 'epps_reseller_logo': epps_reseller_logo_id}));
                    $help.find('a.oe_activate_debug_mode').click(function (e) {
                        e.preventDefault();
                        window.location = $.param.querystring( window.location.href, 'debug');
                    });
                    new instance.web.Dialog(this, {
                        size: 'large',
                        dialogClass: 'oe_act_window',
                        title: _t("About Conformio "),
                    }, $help).open();
                });

            });
        },

    });
    
    /*
     * Hide items from more menu
     */

    instance.web.Sidebar = instance.web.Sidebar.extend({
         add_items: function(section_code, items) {
            //allow superadmin user to see all
            if (this.session.uid == SUPERUSER_ID) {
                this._super.apply(this, arguments);
            }
            else {
                var labels = [_t("Share"),_t("Embed")]; // Array of menuitems to hide from More menu, add more items here
                var new_items = items;
                if (section_code == 'other') {
                    new_items = [];
                    for (var i = 0; i < items.length; i++) {
                        //console.log("items[i]: ", items[i]);
                        if ($.inArray(items[i]['label'], labels) === -1) {
                            new_items.push(items[i]);
                        };
                    };
                };
                if (new_items.length > 0) {
                    this._super.call(this, section_code, new_items);
                };
            }          
        },
    });
   
 
};

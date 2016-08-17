/*!
 * This software is © copyright 2016 EPPS Services Ltd and licensed under the
 * GNU Affero General Public License, version 3.0 as published by the Free
 * Software Foundation.
 */

openerp.epps_account_settings = function(instance, local) {
    var _t = instance.web._t,
        _lt = instance.web._lt;
    var QWeb = instance.web.qweb;
    
    local.AccountSettings = instance.Widget.extend({
        template: "EppsAccountSettingsTemplate",
        //this is used to pas the parameters to template
        init: function(parent) {
            this._super(parent);
            this.name = "Mordecai";
        },

        start: function() {
            this.$el.parent().parent().css( "background-color", "#EDF0F0" );
        },
    });

    instance.web.client_actions.add('epps_user.account_settings', 'instance.epps_user.AccountSettings');
 
};

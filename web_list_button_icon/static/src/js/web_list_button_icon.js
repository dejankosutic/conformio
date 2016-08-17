openerp.web_list_button_icon = function(instance) {
    var _t = instance.web._t,
        _lt = instance.web._lt;
    var QWeb = instance.web.qweb;

    instance.web.list.Button.include({
        format: function(row_data, options) {
            var res = this._super(row_data, options);
            options = options || {};
            var attrs = {};
            if (options.process_modifiers !== false) {
                attrs = this.modifiers_for(row_data);
            }
            if (attrs.invisible) { return ''; }
            if (this.icon && (/\//.test(this.icon))) {
                var template = 'ListView.row.button.icon';
                return QWeb.render(template, {
                    widget: this,
                    prefix: instance.session.prefix,
                    disabled: attrs.readonly
                        || isNaN(row_data.id.value)
                        || instance.web.BufferedDataSet.virtual_id_regex.test(row_data.id.value)
                });
            }
            else {
                return res;
            }
        }
    });
}
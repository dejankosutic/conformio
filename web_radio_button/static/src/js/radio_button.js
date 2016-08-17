openerp.web_radio_button = function(instance) {
    var _t = instance.web._t,
        _lt = instance.web._lt;
    var QWeb = instance.web.qweb;

    /*custom radio button*/
    instance.web.form.FieldButtonRadio = instance.web.form.AbstractField.extend(instance.web.form.ReinitializeFieldMixin, {
    template: 'FieldButtonRadio',
    events: {
        'click input': 'click_change_value'
    },
    init: function(field_manager, node) {
        /* Radio button widget: Attributes options:
        * - "horizontal" to display in column
        * - "no_radiolabel" don't display text values
        */
        this._super(field_manager, node);
        this.selection = _.clone(this.field.selection) || [];
        this.domain = false;
    },
    initialize_content: function () {
        this.uniqueId = _.uniqueId("radio_button");
        this.on("change:effective_readonly", this, this.render_value);
        this.field_manager.on("view_content_has_changed", this, this.get_selection);
        this.get_selection();
    },
    click_change_value: function (event) {
        var val = $(event.target).val();
        val = this.field.type == "selection" ? val : +val;
        if (val !== this.get_value()) {
            this.set_value(val);
        }
    },
    /** Get the selection and render it
     *  selection: [[identifier, value_to_display], ...]
     *  For selection fields: this is directly given by this.field.selection
     *  For many2one fields:  perform a search on the relation of the many2one field
     */
    get_selection: function() {
        var self = this;
        var selection = [];
        var def = $.Deferred();
        if (self.field.type == "many2one") {
            var domain = instance.web.pyeval.eval('domain', this.build_domain()) || [];
            if (! _.isEqual(self.domain, domain)) {
                self.domain = domain;
                var ds = new instance.web.DataSetStatic(self, self.field.relation, self.build_context());
                ds.call('search', [self.domain])
                    .then(function (records) {
                        ds.name_get(records).then(function (records) {
                            selection = records;
                            def.resolve();
                        });
                    });
            } else {
                selection = self.selection;
                def.resolve();
            }
        }
        else if (self.field.type == "selection") {
            selection = self.field.selection || [];
            def.resolve();
        }
        return def.then(function () {
            if (! _.isEqual(selection, self.selection)) {
                self.selection = _.clone(selection);
                self.renderElement();
                self.render_value();
            }
        });
        },
        set_value: function (value_) {
            if (value_) {
                if (this.field.type == "selection") {
                    value_ = _.find(this.field.selection, function (sel) { return sel[0] == value_;});
                }
                else if (!this.selection.length) {
                    this.selection = [value_];
                }
            }
            this._super(value_);
        },
        get_value: function () {
            var value = this.get('value');
            return value instanceof Array ? value[0] : value;
        },
        render_value: function () {
            var self = this;
            this.$el.toggleClass("oe_readonly", this.get('effective_readonly'));
            this.$("input:checked").prop("checked", false);
            this.$("input").filter(function () {return this.value == self.get_value();}).prop("checked", true);
            this.$(".oe_radio_readonly").text(this.get('value') ? this.get('value')[1] : "");
        }
    });
    
    /*adds the widget to the list of field widgets('widget='buttonRadio'')*/
    instance.web.form.widgets.add('buttonRadio', 'instance.web.form.FieldButtonRadio');
}
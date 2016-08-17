/*!
 * This software is © copyright 2016 EPPS Services Ltd and licensed under the
 * GNU Affero General Public License, version 3.0 as published by the Free
 * Software Foundation.
 */

openerp.epps_project = function(instance) {
    var _t = instance.web._t;
    var QWeb = instance.web.qweb;

    instance.mail.RecordThread.include({
        init: function (parent, node) {
                this._super.apply(this, arguments);
                this.node = _.clone(node);
                this.node.params = _.extend({
                    'display_indented_thread': 1,
                    'show_reply_button': true,
                    'show_read_unread_button': true,
                    'read_action': 'unread',
                    'show_record_name': false,
                    'show_compact_message': 1,
                    'display_log_button' : false,
                }, this.node.params);

                }
             });
    //commented out for now
    /*
    instance.web.Menu.include({
        on_needaction_loaded: function(data) {
            var self = this;
            this.needaction_data = data;
            _.each(this.needaction_data, function (item, menu_id) {
                var $item = self.$secondary_menus.find('a[data-menu="' + menu_id + '"]');
                $item.find('.badge').remove();
                if (item.needaction_counter && item.needaction_counter > 0) {
                    var $item = self.$secondary_menus.find('a[data-menu="' + menu_id + '"]');
                    $item.append(QWeb.render("Menu.needaction_counter", { widget : item }));

                    // List of menu-items to hide the counters from
                    var _oe_counters_hidden_on_menu_buttons = [
                    {'model':'epps_project', 'menu':'epps_menu_all_projects'},
                    {'model':'epps_project', 'menu':'epps_repository_menu'}];

                    // Remove button counters
                    _oe_counters_hidden_on_menu_buttons.forEach(function(item){
                        var menu_obj_ref = new openerp.Model('ir.model.data');
                        menu_obj_ref.call('get_object_reference', [item.model, item.menu])
                           .then(function (obj) {
                              if (obj){
                                  if(String(obj[1]) === menu_id){
                                     var $item = self.$secondary_menus.find('a[data-menu="' + obj[1] + '"]');
                                     $item.find('.badge.pull-right').remove();
                                  }
                              }
                           });
                    });
                }
            });
        },
    });*/

    instance.web.FormView.include({
        init_pager: function() {
            self = this;
            this._super();

            if (this.dataset) {
                var _cont = this.dataset.context;
                if (_cont) {
                    if (_cont.task_ids) {
                          self.$el.find('.decod_pager_group').show();
                    }
                }
            }

            this.$el.find('.decod_pager_group').on('click','a[data-pager-action]',function() {
                var $el = $(this);
                if ($el.attr("disabled"))
                    return;
                var action = $el.data('pager-action');
                var def = $.when(self.execute_list_pager_action(action));
                $el.attr("disabled");
                def.always(function() {
                    $el.removeAttr("disabled");
                });
            });
        },
        execute_list_pager_action: function(action) {
            if (!this.dataset.parent_view)
                return;
            var _cont = this.dataset.parent_view.dataset.context;
            if (!_cont)
                return;
            if (!_cont.task_ids)
                return;
            var c_id = _cont.task_ids.indexOf(_cont.self_id);
            var _res_id = 0;
            if (_cont.task_ids.length <= 0)
                return;
            if (this.can_be_discarded()) {
                switch (action) {
                    case 'first':
                        c_id = 0;
                        break;
                    case 'previous':
                        if (c_id -1 < 0)
                            c_id = _cont.task_ids.length-1; // loop around
                        else
                            c_id = c_id -1;
                        break;
                    case 'next':
                        if (c_id +1 >= _cont.task_ids.length)
                            c_id = 0;    // loop around
                        else
                            c_id = c_id+1;
                        break;
                    case 'last':
                        c_id = _cont.task_ids.length-1;
                        break;
                }
                _res_id = _cont.task_ids[c_id];
                _cont.self_id = _res_id;
                var action = {
                    type: 'ir.actions.act_window',
                    res_model: 'project.task',
                    view_mode: 'form',
                    view_type: 'form',
                    views: [[false, 'form']],
                    target: 'new',
                    readonly: true,
                    res_id : _res_id,
                    context: _cont,
                };
                instance.client.action_manager.do_action(action);
            }
            return;
        },
    });


    /*
    Save editable listview items on loose focus, i.e. commit to database
    */
    instance.web.ListView.include({
        init: function () {
            var self = this;
            this._super.apply(this, arguments);

            this.saving_mutex = new $.Mutex();

            this._force_editability = null;
            this._context_editable = false;
            this.editor = this.make_editor();
            // Stores records of {field, cell}, allows for re-rendering fields
            // depending on cell state during and after resize events
            this.fields_for_resize = [];
            instance.web.bus.on('resize', this, this.resize_fields);

            $(this.groups).bind({
                'edit': function (e, id, dataset) {
                    self.do_edit(dataset.index, id, dataset);
                },
                'saved': function () {
                    if (self.groups.get_selection().length) {
                        return;
                    }
                    self.configure_pager(self.dataset);
                    self.compute_aggregates();
                }
            });

            this.records.bind('remove', function () {
                if (self.editor.is_editing()) {
                    self.cancel_edition();
                }
            });

            this.records.bind('add', this.proxy("save_m2m"));
            this.records.bind('remove', this.proxy("save_m2m"));

            this.on('edit:before', this, function (event) {
                if (!self.editable() || self.editor.is_editing()) {
                    event.cancel = true;
                }
            });
            this.on('edit:after', this, function () {
                self.$el.add(self.$buttons).addClass('oe_editing');
                self.$('.ui-sortable').sortable('disable');
            });
            this.on('save:after cancel:after', this, function () {
                self.$('.ui-sortable').sortable('enable');
                self.$el.add(self.$buttons).removeClass('oe_editing');
            });
        },

        save_m2m: function () { // TODO check this!!!!
        //console.log (this.model);
            if (this.model === "project.task" || this.model === "project.project" || this.model === "project.pad" || this.model === 'ir.attachment' || this.model.endsWith(".conbase.pad")) {
                //console.log (this.dataset);
                if (this.dataset.m2m) {
                    if (this.dataset.m2m){
                       // if (this.dataset.m2m.name === 'task_ids') {
                            this.dataset.m2m.view.save().done(function(result) {
                               // self.trigger("save", result);
                            });
                       // }
                    }
                }
                if (this.dataset.o2m) {
                    if (this.dataset.o2m){
                       // if (this.dataset.m2m.name === 'task_ids') {
                            this.dataset.o2m.view.save().done(function(result) {
                               // self.trigger("save", result);
                            });
                       // }
                    }
                }
            }
        },
        ensure_saved: function () {
            return this.save_edition().then(function (saveInfo) {
                if (!saveInfo) { return null; }
                    saveInfo.record.trigger("save", saveInfo.record);
                    return saveInfo;
              });
          },
       
       /** DECODIO
        * TO DO make extensive testing
        * Make Tree View editable inline even when grouped
        * On create returns editing form view 
        * (it's not really possible to know where to create the new record)
        * **/

        editable: function () {
            if (this.grouped) {
                return !this.options.disable_editable_mode
                 && (this.fields_view.arch.attrs.editable
                 || this._context_editable
                 || this.options.editable);
                
            }
            else {
                return this._super();
            }
        },
        do_add_record: function () {
            var self = this;
            if (this.grouped) {
                this.select_record(null);
            }
            else {
                this._super();
            }
        },
    });


    instance.web.ListView.List.include({
        render: function () {
            this._super();
            this.add_project_list_buttons_info();
        },

        add_project_list_buttons_info: function(){
            this.$current.find('tr[data-id]')
                .find( 'td[data-field="edit_current"]' )
                .append( '<span class="list_view_project_buttons_info">Edit</span>' );
            this.$current.find('tr[data-id]')
                .find( 'td[data-field="duplicate_current"]' )
                .append( '<span class="list_view_project_buttons_info">Duplicate</span>' );
            this.$current.find('tr[data-id]')
                .find( 'td[data-field="archive_current"]' )
                .append( '<span class="list_view_project_buttons_info">Archive</span>' );
            this.$current.find('tr[data-id]')
                .find( 'td[data-field="unarchive_current"]' )
                .append( '<span class="list_view_project_buttons_info">Unarchive</span>' );
            this.$current.find('tr[data-id]')
                .find( 'td[data-field="delete_current"]' )
                .append( '<span class="list_view_project_buttons_info">Delete</span>' );
        },
    });
};

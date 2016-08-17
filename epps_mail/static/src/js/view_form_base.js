/*!
 * This software is © copyright 2016 EPPS Services Ltd and licensed under the
 * GNU Affero General Public License, version 3.0 as published by the Free
 * Software Foundation.
 */

openerp.epps_mail = function(instance) {    // DECOD.IO
    var module = instance.mail; //loading the namespace of the 'mail' module

    module.ThreadComposeMessage.include({
        template: 'mail.compose_message',
        bind_events: function (){
            this._super();    //calling the original method in class mail.ThreadComposeMessage

            /* stack for don't close the compose form if the user click on a button */
            this.$('.oe_msg_left, .oe_msg_center').on('mousedown', _.bind( function () { this.stay_open = true; }, this));
            //this.$('.oe_msg_left, .oe_msg_content').on('mouseup', _.bind( function () { this.$('textarea').focus(); }, this));
            var ev_stay = {};
            ev_stay.mouseup = ev_stay.keydown = ev_stay.focus = function () { self.stay_open = false; };
            this.$('textarea').on(ev_stay);
            this.$('textarea').autosize();

            this.$input = this.$('textarea');
            this.$mention_partner_tags = this.$('.o_composer_mentioned_partners');
            this.$mention_dropdown = this.$('.o_composer_mention_dropdown');

            this.$('.o_composer_input').on('keydown', _.bind( this.on_keydown, this));
            this.$('.o_composer_input').on('keyup', _.bind( this.on_keyup, this));


            this.on('change:mention_partners', this, this.render_mention_partners);
            //this.on('change:mention_selected_partners', this, this.render_mention_selected_partners);


            this.$('textarea').off('blur');
            $('.oe_msg_composer').off('blur');
            $('.oe_msg_composer').on('blur', self.on_toggle_quick_composer); // TODO, check this, put focus on element

/*
            console.log('this');
            console.log(this);
            console.log(this.$('.oe_msg_composer'));
            console.log($('.oe_msg_composer'));
*/
            //this.$('textarea').trigger("blur");
/*

$(window).off('taskloaded');
$(window).on("taskloaded", function(){


});


$(window).trigger("taskloaded");
*/

            this.$exampleMulti = this.$('.mentioned_rec');
            this.$exampleMulti.select2();
        },
        init : function (parent, datasets, options) {
            this._super(parent, datasets, options);
            this.show_compact_message = false;
            this.show_delete_attachment = true;
            this.is_log = false;
            this.recipients = [];
            this.recipient_ids = [];
            this.all_partner_ids = [];

            console.log('init');

            this.options = _.defaults(options || {}, {
                context: {},
                mention_delimiter: '@',
                mention_min_length: 2,
                mention_typing_speed: 400,
                mention_fetch_limit: 8,
            });
            this.PartnerModel = new instance.web.Model('res.partner');

            instance.web.qweb.add_template('/epps_mail/static/src/xml/epps_mail.xml');

            var self = this;
            this.PartnerModel.query(['id', 'name', 'email']).all().then(function(result) {
                                _.each(result, function(item) {
                                    self.all_partner_ids.push({'id' : item.id, 'name' : item.name, 'email' : item.email});
                                });
                            })
            this.set('mention_partners', []); // proposition of not-mention partner matching the mention_word
            this.set('mention_selected_partners', []); // contains the mention partners sorted as they appear in the input text
            instance.web.bus.on('clear_uncommitted_changes', this, function(e) {
                if (this.show_composer && !e.isDefaultPrevented()){
                    if (!confirm(_t("You are currently composing a message, your message will be discarded.\n\nAre you sure you want to leave this page ?"))) {
                        e.preventDefault();
                    }
                    else{
                        this.on_cancel();
                    }
                }
            });
        },

        on_compose_fullmail: function (default_composition_mode) {
            var self = this;
            if(!this.do_check_attachment_upload()) {
                return false;
            }
            var _partners = self.$exampleMulti.select2("val");
            for (var i=0; i<_partners.length; i++) {
                var partid = $.grep(this.all_partner_ids, function(e){ return e.id == parseInt(_partners[i], 10); });
                for (var j=0; j<partid.length; j++) {
                    self.recipients.push({  'full_name': partid[j].name,
                        'name': partid[j].name,
                        'email_address': partid[j].email,
                        'partner_id': parseInt(partid[j].id, 10),
                        'checked': true,
                        'reason': 'Incoming email author'
                    });
                }
            }
            var recipient_done = $.Deferred();
            if (this.is_log) {
                recipient_done.resolve([]);
            }
            else {
                recipient_done = this.check_recipient_partners();
            }
            $.when(recipient_done).done(function (partner_ids) {
                var context = {
                    'default_parent_id': self.id,
                    'default_body': module.ChatterUtils.get_text2html(self.$el ? (self.$el.find('textarea:not(.oe_compact)').val() || '') : ''),
                    'default_attachment_ids': _.map(self.attachment_ids, function (file) {return file.id;}),
                    'default_partner_ids': partner_ids,
                    'default_is_log': self.is_log,
                    'mail_post_autofollow': false,
                    'mail_post_autofollow_partner_ids': partner_ids,
                    'is_private': self.is_private
                };
                if (default_composition_mode != 'reply' && self.context.default_model && self.context.default_res_id) {
                    context.default_model = self.context.default_model;
                    context.default_res_id = self.context.default_res_id;
                }

                var action = {
                    type: 'ir.actions.act_window',
                    res_model: 'mail.compose.message',
                    view_mode: 'form',
                    view_type: 'form',
                    views: [[false, 'form']],
                    target: 'new',
                    context: context,
                };

                self.do_action(action, {
                    'on_close': function(){ !self.parent_thread.options.view_inbox && self.parent_thread.message_fetch_last() }
                });
                self.on_cancel();
            });

        },

    preprocess_message: function () {
        // Return a deferred as this function is extended with asynchronous
        // behavior for the chatter composer
            return $.when({
                content: this.mention_preprocess_message(this.$input.val()),
                attachment_ids: _.pluck(this.get('attachment_ids'), 'id'),
                partner_ids: _.pluck(this.get('mention_selected_partners'), 'id'),
            });
        },

    // Others
    get_selection_positions: function () {
        var el = this.$input.get(0);
        return el ? {start: el.selectionStart, end: el.selectionEnd} : {start: 0, end: 0};
    },

    set_cursor_position: function (pos) {
        this.$input.each(function (index, elem) {
            if (elem.setSelectionRange){
                elem.setSelectionRange(pos, pos);
            }
            else if (elem.createTextRange){
                elem.createTextRange().collapse(true).moveEnd('character', pos).moveStart('character', pos).select();
            }
        });
    },
        reinit: function() {
            this.set('mention_partners', []); // proposition of not-mention partner matching the mention_word
            this.set('mention_selected_partners', []); // contains the mention partners sorted as they appear in the input text
            this._super();
        },

        on_message_post: function (event) {
            var self = this;
            var _partners = self.$exampleMulti.select2("val");
            for (var i=0; i<_partners.length; i++) {
                var partid = $.grep(this.all_partner_ids, function(e){ return e.id == parseInt(_partners[i], 10); });
                for (var j=0; j<partid.length; j++) {
                    self.recipients.push({  'full_name': partid[j].name,
                        'name': partid[j].name,
                        'email_address': partid[j].email,
                        'partner_id': parseInt(partid[j].id, 10),
                        'checked': true,
                        'reason': 'Incoming email author'
                    });
                }
            }

            this._super(event);
        },



        on_keydown: function (event) {
            switch(event.which) {

                // UP, DOWN: prevent moving cursor if navigation in mention propositions
                case $.ui.keyCode.UP:
                case $.ui.keyCode.DOWN:
                    if (this.get('mention_partners').length) {
                        event.preventDefault();
                    }
                    break;
                // BACKSPACE, DELETE: check if need to remove a mention
                case $.ui.keyCode.BACKSPACE:
                case $.ui.keyCode.DELETE:
                    this.mention_check_remove();
                    break;
                // ENTER: submit the message only if the dropdown mention proposition is not displayed
                case $.ui.keyCode.ENTER:

                    if (!this.get('mention_partners').length) {
                        //this.send_message();
                    } else {
                        event.preventDefault();
                    }
                    break;
            }
        },

        on_keyup: function (event) {
            switch(event.which) {
                // ESCAPED KEYS: do nothing
                case $.ui.keyCode.END:
                case $.ui.keyCode.PAGE_UP:
                case $.ui.keyCode.PAGE_DOWN:
                    break;
                // ESCAPE: close mention propositions
                case $.ui.keyCode.ESCAPE:
                    this.set('mention_partners', []);
                    break;
                // ENTER, UP, DOWN: check if navigation in mention propositions
                case $.ui.keyCode.ENTER:
                case $.ui.keyCode.UP:
                case $.ui.keyCode.DOWN:
                    this.mention_proposition_navigation(event.which);
                    break;
                // Otherwise, check if a mention is typed
                default:
                    this.mention_word = this.mention_detect_delimiter();
                    if (this.mention_word) {
                        this.mention_word_changed();
                    } else {
                        this.set('mention_partners', []); // close the dropdown
                    }
            }
        },

        // Mention
        on_click_mention_item: function (event) {
            event.preventDefault();

            var text_input = this.$input.val();
            var partner_id = $(event.currentTarget).data('partner-id');
            var selected_partner = _.filter(this.get('mention_partners'), function (p) {
                return p.id === partner_id;
            })[0];

            // add the mention partner to the list
            var mention_selected_partners = this.get('mention_selected_partners');
            if (mention_selected_partners.length) { // there are already mention partners
                // get mention matches (ordered by index in the text)
                var matches = this.mention_get_match(text_input);
                var index = this.mention_get_index(matches, this.get_selection_positions().start);
                mention_selected_partners.splice(index, 0, selected_partner);
                mention_selected_partners = _.clone(mention_selected_partners);
            } else { // this is the first mentionned partner
                mention_selected_partners = mention_selected_partners.concat([selected_partner]);
            }
            this.set('mention_selected_partners', mention_selected_partners);

            this.$exampleMulti.val(this.$exampleMulti.select2("val").concat(selected_partner.id)).trigger("change");

            // update input text, and reset dropdown
            var cursor_position = this.get_selection_positions().start;
            var text_left = text_input.substring(0, cursor_position-(this.mention_word.length+1));
            var text_right = text_input.substring(cursor_position, text_input.length);
            var text_input_new = text_left + this.options.mention_delimiter + selected_partner.name + ' ' + text_right;
            this.$input.val(text_input_new);
            this.set_cursor_position(text_left.length+selected_partner.name.length+2);
            this.set('mention_partners', []);
        },

        on_hover_mention_proposition: function (event) {
            var $elem = $(event.currentTarget);
            this.$('.o_mention_proposition').removeClass('active');
            $elem.addClass('active');
        },

        mention_proposition_navigation: function (keycode) {
            var $active = this.$('.o_mention_proposition.active');
            if (keycode === $.ui.keyCode.ENTER) { // selecting proposition
                $active.click();
            } else { // navigation in propositions
                var $to;
                if (keycode === $.ui.keyCode.DOWN) {
                    $to = $active.next('.o_mention_proposition:not(.active)');
                } else {
                    $to = $active.prev('.o_mention_proposition:not(.active)');
                }
                if ($to.length) {
                    $active.removeClass('active');
                    $to.addClass('active');
                }
            }
        },

        /**
         * Return the text attached to the mention delimiter
         * @returns {String|false}: the text right after the delimiter or false
         */
        mention_detect_delimiter: function () {
            var options = this.options;
            var delimiter = options.mention_delimiter;
            var text_val = this.$input.val();
            var cursor_position = this.get_selection_positions().start;
            var left_string = text_val.substring(0, cursor_position);
            var search_str = text_val.substring(left_string.lastIndexOf(delimiter) - 1, cursor_position);

            return validate_keyword(search_str);

            function validate_keyword (search_str) {
                var pattern = "(^"+delimiter+"|(^\\s"+delimiter+"))";
                var regex_start = new RegExp(pattern, "g");
                search_str = search_str.replace(/^\s\s*|^[\n\r]/g, '');
                if (regex_start.test(search_str) && search_str.length > options.mention_min_length) {
                    search_str = search_str.replace(pattern, '');
                    return search_str.indexOf(' ') < 0 && !/[\r\n]/.test(search_str) ? search_str.replace(delimiter, '') : false;
                }
                return false;
            }
        },

        mention_word_changed: function () {
            var self = this;
            // start a timeout to fetch partner with the current 'mention word'. The timer avoid to start
            // an RPC for each pushed key when the user is typing the partner name.
            // The 'mention_typing_speed' option should approach the time for a human to type a letter.
            clearTimeout(this.mention_fetch_timer);
            this.mention_fetch_timer = setTimeout(function () {
                self.mention_fetch_partner(self.mention_word);
            }, this.options.mention_typing_speed);
        },

        mention_fetch_partner: function (search_str) {
            var self = this;
            this.PartnerModel
                .query(['id', 'name', 'email'])
                .filter([['user_ids', 'not in', 1],
                        ['is_company', '=', false],
                        ['email', '!=', false],
                        ['id', 'not in', _.pluck(this.get('mention_selected_partners'), 'id')], '|',
                        ['name', 'ilike', search_str], ['email', 'ilike', search_str]])
                .limit(this.options.mention_fetch_limit)
                .all().then(function (partners) {
                    self.set('mention_partners', partners);
                });
        },

        mention_check_remove: function () {
            var mention_selected_partners = this.get('mention_selected_partners');
            var partners_to_remove = [];
            var selection = this.get_selection_positions();
            var deleted_binf = selection.start;
            var deleted_bsup = selection.end;

            var matches = this.mention_get_match(this.$input.val());
            for (var i=0; i<matches.length; i++) {
                var m = matches[i];
                var m1 = m.index;
                var m2 = m.index + m[0].length;
                if (deleted_binf <= m2 && m1 < deleted_bsup) {
                    partners_to_remove.push(mention_selected_partners[i]);
                }
            }
            this.set('mention_selected_partners', _.difference(mention_selected_partners, partners_to_remove));
        },

        mention_preprocess_message: function (message) {
            var partners = this.get('mention_selected_partners');
            if (partners.length) {
                var matches = this.mention_get_match(message);
                var substrings = [];
                var start_index = 0;
                for (var i=0; i<matches.length; i++) {
                    var match = matches[i];
                    var end_index = match.index + match[0].length;
                    var partner_name = match[0].substring(1);
                    var processed_text = _.str.sprintf("<a href='#' class='o_mail_redirect' data-oe-model='res.partner' data-oe-id='%s'>%s</a>", partners[i].id, partner_name);
                    var subtext = message.substring(start_index, end_index).replace(match[0], processed_text);
                    substrings.push(subtext);
                    start_index = end_index;
                }
                substrings.push(message.substring(start_index, message.length));
                return substrings.join('');
            }
            return message;
        },

        render_mention_partners: function () {
            if (this.get('mention_partners').length) {
                this.$mention_dropdown.html(instance.web.qweb.render('epps_mail.ChatComposer.MentionMenu', {
                    partners: this.get('mention_partners'),
                }));
                this.$mention_dropdown.addClass('open');
            } else {
                this.$mention_dropdown.removeClass('open');
                this.$mention_dropdown.empty();
            }

            this.$('.o_mention_proposition').on('click', _.bind( this.on_click_mention_item, this));
            this.$('.o_mention_proposition').on('mouseover', _.bind( this.on_hover_mention_proposition, this));
        },

        /*render_mention_selected_partners: function () {
            this.$mention_partner_tags.html(session.web.qweb.render('mail.ChatComposer.MentionTags', {
                partners: this.get('mention_selected_partners'),
            }));
        },*/

        /**
         * Return the matches (as RexExp.exec does) for the partner mention in the input text
         * @param {String} input_text: the text to search matches
         * @returns {Object[]} matches in the same format as RexExp.exec()
         */
        mention_get_match: function (input_text) {
            var self = this;
            // create the regex of all mention partner name
            var partner_names = _.pluck(this.get('mention_selected_partners'), 'name');
            var escaped_partner_names = _.map(partner_names, function (str) {
                return "("+_.str.escapeRegExp(self.options.mention_delimiter+str)+")";
            });
            var regex_str = escaped_partner_names.join('|');
            // extract matches
            var result = [];
            if(regex_str.length){
                var myRegexp = new RegExp(regex_str, 'g');
                var match = myRegexp.exec(input_text);
                while (match !== null) {
                    result.push(match);
                    match = myRegexp.exec(input_text);
                }
            }
            return result;
        },

        mention_get_index: function (matches, cursor_position) {
            for (var i=0; i<matches.length; i++) {
                if (cursor_position <= matches[i].index) {
                    return i;
                }
            }
            return i;
        },

        /* do post a message and fetch the message */
        do_send_message_post: function (partner_ids, log) {
            var self = this;
            var values = {
                'body': this.$('textarea').val(),
                'subject': false,
                'parent_id': this.context.default_parent_id,
                'attachment_ids': _.map(this.attachment_ids, function (file) {return file.id;}),
                'partner_ids': partner_ids,
                'context': _.extend(this.parent_thread.context, {
                    'mail_post_autofollow': false,
                    'mail_post_autofollow_partner_ids': partner_ids,
                }),
                'type': 'comment',
                'content_subtype': 'plaintext',
            };
            if (log) {
                values['subtype'] = false;
            }
            else {
                values['subtype'] = 'mail.mt_comment';
            }
            this.parent_thread.ds_thread._model.call('message_post', [this.context.default_res_id], values).done(function (message_id) {
                var thread = self.parent_thread;
                var root = thread == self.options.root_thread;
                if (self.options.display_indented_thread < self.thread_level && thread.parent_message) {
                    var thread = thread.parent_message.parent_thread;
                }
                // create object and attach to the thread object
                thread.message_fetch([["id", "=", message_id]], false, [message_id], function (arg, data) {
                    var message = thread.create_message_object( data.slice(-1)[0] );
                    // insert the message on dom
                    console.log('do_send_message_post');
                    thread.insert_message( message, root ? undefined : self.$el, true );
                });
                self.on_cancel();
                self.flag_post = false;
            });
        },




    });


    module.Thread.include({


        message_fetch_last: function (replace_domain, replace_context, ids, callback) {
            return this.ds_message.call('message_read', [
                    // ids force to read
                    ids === false ? undefined : ids && ids.slice(0, 1),
                    // domain + additional
                    (replace_domain ? replace_domain : this.domain),
                    // ids allready loaded
                    (this.id ? [this.id].concat( this.get_child_ids() ) : this.get_child_ids()),
                    // option for sending in flat mode by server
                    this.options.flat_mode,
                    // context + additional
                    (replace_context ? replace_context : this.context),
                    // parent_id
                    this.context.default_parent_id || undefined,
                    1,
                ]).done(callback ? _.bind(callback, this, arguments) : this.proxy('switch_new_message_prepend')
                ).done(this.proxy('message_fetch_set_read'));
        },
        switch_new_message_prepend: function (records, dom_insert_after) {
            var self=this;
            var dom_insert_after = typeof dom_insert_after == 'object' ? dom_insert_after : false;
            _(records).each(function (record) {
                var thread = self.browse_thread({
                    'id': record.parent_id,
                    'default_return_top_thread':true
                });
                // create object and attach to the thread object
                var message = thread.create_message_object( record );
                // insert the message on dom
                thread.insert_message( message, dom_insert_after, true);
            });
            if (!records.length && this.options.root_thread == this) {
                this.no_message();
            }
        },

    });



    /**  DECODIO:
     * UserMenu
     * ------------------------------------------------------------
     *
     * Add a link on the top user bar for write a full mail
     */
    instance.web.ComposeMessageTopButton = instance.web.Widget.extend({
        template:'epps_mail.ComposeMessageTopButton',

        start: function () {
            this.$el.on('click', this.on_compose_message);
            this._super();
        },

        on_compose_message: function (event) {
            event.preventDefault();
            event.stopPropagation();
            var action = {
                type: 'ir.actions.act_window',
                res_model: 'mail.compose.message',
                view_mode: 'form',
                view_type: 'form',
                views: [[false, 'form']],
                target: 'new',
                context: {'direct_message': true,},
                /*in xml use => invisible="context.get('direct_message', False) == True" */
            };
            instance.client.action_manager.do_action(action);
        },
    });

    instance.web.UserMenu.include({
        do_update: function(){
            var self = this;
            this._super.apply(this, arguments);
            this.update_promise.then(function() {
                var mail_button = new instance.web.ComposeMessageTopButton();
                mail_button.appendTo(instance.webclient.$el.parents().find('.oe_systray'));
                openerp.web.bus.trigger('resize');  // Re-trigger the reflow logic
            });
        },
    });

};

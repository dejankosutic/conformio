/*!
 * This software is © copyright 2016 EPPS Services Ltd and licensed under the
 * GNU Affero General Public License, version 3.0 as published by the Free
 * Software Foundation.
 */

openerp.epps_reduced_repository = function(instance) {
    var _t = instance.web._t,
        _lt = instance.web._lt;
    var QWeb = instance.web.qweb;

    var _DEBUG = true;
    var VIEW_BROWSER = 1;
    var VIEW_PREVIEW = 2;
    var VIEW_EDIT = 3;

    instance.project_files.include({
    init: function (parent, node) {
            var self = this;
            //console.log('init');
            //get the options from xml
            if (node.attrs.options){
                self.is_repository = node.attrs.options.is_repository || false;
            }

            self.path_trace = [];
            self.actions_attrs = {};
            self.action_managers = [];

            this._super(parent, node);
        },

        display_folder_content: function(folderID, parentID) {
            var self = this;

            if (instance.session.debug)
                console.log('display_folder_content');
            
            //first call the super needs testing not working makes duplicate directories
            //this._super(folderID, parentID);

            var myFolderID = self.projectFolderID;
            if (folderID)
                myFolderID = parseInt(folderID);

            //myFolderID = parseInt(self.path_trace[self.path_trace_depth].id);
            self.currentFolder = myFolderID;
            //self.diplay_crums();

            self.ir_attachment.call('calculate_breadcrums_fold', [self.currentFolder, self.projectID]).done(function (ret) {
                self.path_trace = ret;
                self.diplay_crums();
            });

            var previous = self.get_parent_id();
            if (parentID)
                previous = parentID;

            var _displayedFiles = 0;
            if (instance.session.debug) {
                console.log('display_folder_content');
                console.log(myFolderID);
                console.log(self.currentFolder);
                console.log(self.projectFolderID);
            }
            self.view_change(VIEW_BROWSER);

            res = QWeb.render('project_file_browser',{'is_repository': self.is_repository});
            res = $(res);

            var content = '<table class="oe_file_table" id="project_files_table">';
            content += '<tr class="oe_project_files_header_row">';
            content += '<td class="file_table_icon"></td>';
            content += '<td class="file_table_name">' + _t('Name') + '</td>';
            content += '<td>' + _t('Author') + '</td>';
            content += '<td>' + _t('Modified') + '</td>';
            content += '<td>' + _t('Shared with') + '</td>';
            content += '<td>' + _t('Status') + '</td>';
            content += '<td class="file_table_checkbox"><input type="checkbox" name="select_row" id="files_select_all_rows"/></td>';
            content += '</tr>';

            if (self.currentFolder != self.projectFolderID) {
                var _r_dir = {
                    icon: '/epps_design/static/src/img/folder-back-icon.png',
                    id: previous,
                    name: '..',
                    author: '',
                    author_id: '',
                    modified: '',
                    shared: '',
                    status: '',
                    type: 'back',
                };
                content += QWeb.render('project_file_folder', { dir : _r_dir, is_repository: self.is_repository});
            }

            if (self.is_my_files) {
                if (self.projectFolderID == self.rootFolderID && myFolderID == self.rootFolderID) {
                    // get all projects where user is a member
                    self.display_myfolder_by_id(myFolderID, content, res);
                } else {
                    self.display_folder_by_id(myFolderID, content, res);
                }
            } else {
                self.display_folder_by_id(myFolderID, content, res);
            }
        },
        sync_visible: function() {
            var self = this;
            console.log('sync_visible');
            if (self.selectedFolders == 1)
                return true;
            return false;
        },
        //removing all context menu buttons except open
        attachContextMenu: function(){
            var self = this;
            self._items = [];
            if (self.is_repository){
                self._items = {
                    "Open": {name: "Open", icon: "oe_open", visible: function(key, opt){ return self.single_selection_folder();}},
                    "See_preview": {name: "See preview", icon: "oe_open", visible: function(key, opt){ return self.single_selection_file();}}
                };
            }
            else if (self.is_my_files){
                self._items = {
                    "Open": {name: "Open", icon: "oe_open", visible: function(key, opt){ return self.single_selection_folder();}},
                    "See_preview": {name: "See preview", icon: "oe_open", visible: function(key, opt){ return self.single_selection_file();}},
                    //"Share": {name: "Share", icon: "oe_share", visible: function(key, opt){ return self.share_visible();}},
                    //"Unshare": {name: "Unshare", icon: "oe_unshare", visible: function(key, opt){ return self.unshare_visble_private_folder();}},
                    //"Make_Private": {name: "Make private", icon: "oe_requestaccess", visible: function(key, opt){ return self.make_private_visible();}},
                    //"Move": {name: "Move", icon: "oe_move"},
                    //"Copy": {name: "Copy", icon: "oe_copy"},
                    //"Rename": {name: "Rename", icon: "oe_rename", visible: function(key, opt){ return self.single_selection();}},
                    //"Delete": {name: "Delete", icon: "oe_delete"},
                    "Create_a_task": {name: "Create a task", icon: "oe_createtask", visible: function(key, opt){ return self.single_selection();}},
                    /*"Sync": {name: "Sync", icon: "oe_synchronize", visible: function(key, opt){ return self.make_private_visible();}},*/
                    //"Request_access": {name: "Request access", icon: "oe_requestaccess", visible: function(key, opt){ return self.share_visible();}},
                    "Previous_versions": {name: "Previous versions", icon: "oe_previousversions", visible: function(key, opt){ return self.single_selection_file();}},
                    "Edit_online": {name: "Edit online", icon: "oe_editinmsoffice", visible: function(key, opt){ return self.single_selection_file();}},
                    "Edit_in_Microsoft_Office": {name: "Edit in Microsoft Office", icon: "oe_editinmsoffice", visible: function(key, opt){ return self.single_selection_file();}},
                };
            }
            else{
                self._items = {
                    "Open": {name: "Open", icon: "oe_open", visible: function(key, opt){ return self.single_selection_folder();}},
                    "See_preview": {name: "See preview", icon: "oe_open", visible: function(key, opt){ return self.single_selection_file();}},
                    "Share": {name: "Share", icon: "oe_share", visible: function(key, opt){ return self.share_visible();}},
                    "Unshare": {name: "Unshare", icon: "oe_unshare", visible: function(key, opt){ return self.unshare_visble_private_folder();}},
                    "Make_Private": {name: "Make private", icon: "oe_requestaccess", visible: function(key, opt){ return self.make_private_visible();}},
    
                    "Move": {name: "Move", icon: "oe_move"},
                    "Copy": {name: "Copy", icon: "oe_copy"},
                    "Rename": {name: "Rename", icon: "oe_rename", visible: function(key, opt){ return self.single_selection();}},
                    "Delete": {name: "Delete", icon: "oe_delete"},
                    "Create_a_task": {name: "Create a task", icon: "oe_createtask", visible: function(key, opt){ return self.single_selection();}},
                    "Sync": {name: "Sync", icon: "oe_synchronize", visible: function(key, opt){ return self.sync_visible();}},
                    "Request_access": {name: "Request access", icon: "oe_requestaccess", visible: function(key, opt){ return self.share_visible();}},
                    "Previous_versions": {name: "Previous versions", icon: "oe_previousversions", visible: function(key, opt){ return self.single_selection_file();}},
                    "Edit_online": {name: "Edit online", icon: "oe_editinmsoffice", visible: function(key, opt){ return self.single_selection_file();}},
                    "Edit_in_Microsoft_Office": {name: "Edit in Microsoft Office", icon: "oe_editinmsoffice", visible: function(key, opt){ return self.single_selection_file();}},
                };
            }

            self.$el.find("#project_files_table").contextMenu({
                selector: 'tr.oe_project_file_row_context',
                events: {
                   show : function(options){
                        this.find( "td.oe_file_row_selector" ).each(function(){
                            if ($(this)[0].children[0])
                                $(this)[0].children[0].checked = true;
                        });
                        self.on_recalculate_selected(self);
                        return true;
                   },
                },
                callback: function(key, options) {
                    //var m = "clicked: " + key + " on " + $(this).text();
                    //console.log($(this));
                    if ($(this) && $(this)[0].dataset) {
                        switch (key) {
                            case "Copy":
                                self.on_copy_folder(self);
                            break;
                            case "Open":
                                self.on_file_open();
                            break;
                            case "See_preview":
                                self.on_file_open();
                            break;
                            case "Move":
                                self.on_move_folder(self);
                            break;
                            case "Delete":
                                self.delete_files_and_folders(self);
                            break;
                            case "Create_a_task":
                                self.create_task(self);
                            break;
                            case "Share":
                                self.share_folder(self);
                            break;
                            case "Unshare":
                                self.unshare_folder(self);
                            break;
                            case "Request_access":
                                self.request_access(self);
                            break;
                            case "Make_Private":
                                self.make_folder_private(self);
                            break;
                            case "Sync":
                                self.sync_folder(self);
                            break;
                            case "Rename":
                                self.on_rename_folder(self);
                            break;
                            case "Previous_versions":
                                self.on_previous_versions(self);
                            break;
                            case "Edit_online":
                                self.edit_online_row(self);
                            break;
                            case "Edit_in_Microsoft_Office":
                                console.log("Edit_in_Microsoft_Office");
                                self.edit_in_ms_word_row(self);
                            break;
                        }

                    }
                    //console.log($(this));
                    //window.console && console.log(m) || alert(m);
                },
                items: self._items,
            });
           // });
        },


        display_folder_by_id: function(myFolderID, content, res) {
            var self = this;
            if (myFolderID) {
                // first get a list of subfolders
                self.document_directory.query()
                     .filter([['parent_id', '=', myFolderID], ['directory_active', '=', 'true']])
                     .all().then(function (_dirs) {
                            _.each(_dirs, function(_dir){
                                var shared_user_ids = _.union(_dir.shared_editors_ids, _dir.shared_reviewers_ids, _dir.shared_viewers_ids, _dir.shared_previewers_ids, _dir.shared_uploaders_ids).sort(function(a,b){return a-b});
                                var _shared = '';
                                for (i = 0; i < shared_user_ids.length; i++)  {
                                    if (i > 2) { // display only first 3 users
                                        break;
                                    }
                                    _shared += '<img src="/web/binary/image?model=res.users&id='+shared_user_ids[i]+'&field=image_small" class="tbl_shared_user"/>';
                                }

                                var _r_dir = {
                                    icon: self.get_folder_icon(_dir),
                                    id: _dir.id,
                                    parent_id: myFolderID,
                                    name: _dir.name,
                                    isPrivate: _dir.isPrivate,
                                    author: _dir.create_uid[1],
                                    author_id: _dir.create_uid[0],
                                    modified: _dir.__last_update,
                                    shared: _shared,
                                    status: '',
                                    type: 'folder',
                                };
                                content += QWeb.render('project_file_folder', { dir : _r_dir});
                            });
                            // get a list of all attachments
                            self.ir_attachment.query(['id', 'type', 'name', 'create_uid', '__last_update', 'document_status_id', 'url', 'file_type_icon'])
                                 .filter([['parent_id', '=', myFolderID], ['file_active', '=', true]])
                                 .all().then(function (_files) {
                                        _.each(_files, function(_file){
                                            var _type = 'file';
                                            if (_file.type == 'url') {
                                                _type = 'url';
                                            }
                                            var _r_dir = {
                                                icon: self.get_file_icon(_file),
                                                id: _file.id,
                                                parent_id: myFolderID,
                                                name: _file.name,
                                                author: _file.create_uid[1],
                                                author_id: _file.create_uid[0],
                                                modified: _file.__last_update,
                                                shared: '',
                                                status: _file.document_status_id[1],
                                                type: _type,
                                                ftype: _file.type,
                                                url: _file.url,
                                            };
                                            content += QWeb.render('project_file_folder', { dir : _r_dir});
                                        });

                                        // display files that belong to tasks under this project
                                        if (self.currentFolder == self.projectFolderID) {
                                            _.each(self.task_files, function(_file){
                                                var _type = 'file';
                                                if (_file.type == 'url') {
                                                    _type = 'url';
                                                }
                                                var _r_dir = {
                                                    icon: self.get_file_icon(_file),
                                                    id: _file.id,
                                                    parent_id: myFolderID,
                                                    name: _file.name,
                                                    author: _file.create_uid[1],
                                                    author_id: _file.create_uid[0],
                                                    modified: _file.__last_update,
                                                    shared: '',
                                                    status: _file.document_status_id[1],
                                                    type: _type,
                                                    ftype: _file.type,
                                                    url: _file.url,
                                                };
                                                content += QWeb.render('project_file_folder', { dir : _r_dir});
                                            });
                                            _.each(self.project_files, function(_file){
                                                var _type = 'file';
                                                if (_file.type == 'url') {
                                                    _type = 'url';
                                                }
                                                var _r_dir = {
                                                    icon: self.get_file_icon(_file),
                                                    id: _file.id,
                                                    parent_id: myFolderID,
                                                    name: _file.name,
                                                    author: _file.create_uid[1],
                                                    author_id: _file.create_uid[0],
                                                    modified: _file.__last_update,
                                                    shared: '',
                                                    status: _file.document_status_id[1],
                                                    type: _type,
                                                    ftype: _file.type,
                                                    url: _file.url,
                                                };
                                                content += QWeb.render('project_file_folder', { dir : _r_dir});
                                            });
                                        }

                                        var _r_dir = {
                                            icon: '/epps_design/static/src/img/file-icon.png',
                                            id: 0,
                                            parent_id: myFolderID,
                                            name: '',
                                            author: '',
                                            author_id: '',
                                            modified: '',
                                            shared: '',
                                            status: '',
                                            type: 'file',
                                        };
                                        content += QWeb.render('project_file_dummy', { dir : _r_dir});
                                        content += '</table>';

                                        if ( res.find( "#oe_project_file_browser_browser" ).length>0) {
                                            res.find( "#oe_project_file_browser_browser" )[0].innerHTML = content;
                                        }
/*
                                        res.find( "tr.oe_project_file_row" ).each(function(){
                                            var p = self.currentFolder;
                                            if ($(this).hasClass('oe_row_folder') && $(this)[0].dataset && $(this)[0].dataset.id) {
                                                p = parseInt($(this)[0].dataset.id);
                                            }

                                            $(this).dropzone({
                                                url: "/web/binary/upload_attachment_parent_zone",
                                                parent_id: p,
                                                project_id: self.projectID,
                                                callback: self.fileupload_id,
                                                clickable: false,
                                            });
                                        });*/
                                        /*res.find( "tr.oe_project_file_row" ).dropzone({
                                            url: "/web/binary/upload_attachment_parent_zone",
                                            parent_id: self.currentFolder,
                                            project_id: self.projectID,
                                            callback: self.fileupload_id,
                                            clickable: false,
                                        });*/

                                        /*res.find( "tr.oe_project_file_row" ).each(function(){
                                            $("tr.oe_project_file_row").dropzone({ url: "/web/binary/upload_attachment_parent" });
                                        });*/

                                        res.find( ".select_file_row" ).each(function(){

                                            $(this).off('click');
                                            $(this).on('click', function(e){
                                                self.on_select_file_row(self, e);
                                            });
                                        });

                                        res.find( "#doclist_new" ).each(function(){
                                            $(this).off('click');
                                            $(this).on('click', function(e){
                                                self.on_add_folder(self, e);
                                            });
                                        });

                                        res.find( "#doclist_new_fold" ).each(function(){
                                            $(this).off('click');
                                            $(this).on('click', function(e){
                                                self.on_add_file(self, e);
                                            });
                                        });

                                        self.$el.find('#oe_project_files_left').empty().append(res);
                                        self.attach_file_browser_events();
                                    });
                        });
            } else {
                console.log('no ID');
            }
        },
    });
}
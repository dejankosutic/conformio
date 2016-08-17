# -*- coding: utf-8 -*-
##############################################################################
# This software is © copyright 2016 EPPS Services Ltd and licensed under the
# GNU Affero General Public License, version 3.0 as published by the Free
# Software Foundation.
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################

import base64
import errno
import logging
import os
import sys
import random
import shutil
import string
import time
from StringIO import StringIO

import psycopg2
import re

import datetime
from lxml import etree
import time

from openerp import SUPERUSER_ID
from openerp import tools
from openerp.addons.resource.faces import task as Task
from openerp.osv import fields, osv
from openerp.tools import float_is_zero
from openerp.tools.translate import _
import urllib2
import uuid

import os
import pprint
import shlex

import dropbox
from dropbox.files import FileMetadata, FolderMetadata
from dropbox.files import WriteMode
from dropbox.exceptions import ApiError, AuthError
from dropbox.client import DropboxOAuth2Flow, DropboxClient
from dropbox.client import DropboxOAuth2FlowNoRedirect
from dropbox import rest as dbrest

_logger = logging.getLogger(__name__)


class DropboxIntegration(osv.Model):
    _name = 'dropbox.integration'
    _description = 'Dropbox Integration'

    def backup(self, cr, uid, ids):
        """Uploads contents of folder to Dropbox."""

        # get current directory
        dp = self.pool['document.directory']
        d = dp.browse(cr, SUPERUSER_ID, ids, context={})

        # get current user
        u = self.pool['res.users'].browse(cr, SUPERUSER_ID, uid, context={})

        # get values from user
        TOKEN = u.dropbox_token
        if TOKEN:
            dbx = dropbox.Dropbox(TOKEN)

            # Check that the access token is valid
            try:
                dbx.users_get_current_account()
            except AuthError as err:
                sys.exit(
                    "ERROR: Invalid access token; try re-generating an access token from the app console on the web.")

            f_path = '/'
            for node in dp.build_folder_path(cr, uid, ids):
                f_path = '/' + node.name + f_path

            ap = self.pool['ir.attachment']
            file_id = ap.search(cr, uid, [('parent_id', '=', d.id)])
            files = ap.browse(cr, uid, file_id, context={})

            def fs(self, cr):
                return tools.config.filestore(cr.dbname)

            path = ''
            full_path = ''
            for file in files:
                # extract file path
                path = file.store_fname
                path = re.sub('[.]', '', path)
                path = path.strip('/\\')
                full_path = os.path.join(fs(self, cr), path)

                # open file
                f = open(full_path, 'rb')

                # upload it to dropbox
                dbx.files_upload(f, f_path + file.name)

            # get subfolders
            d = dp.search(cr, uid, [('parent_id', '=', d.id)])
            for folder in d:
                self.backup(cr, uid, folder)
        return full_path


    def sync_loop(self, cr, uid, dbx, ids):
        """Main loop to sync given folder with Dropbox.
        'dbx' => Dropbox object
        'ids' => 'document.directory' ids to be synced."""

        dp = self.pool['document.directory']
        iap = self.pool['ir.attachment']

        f_path_prefix = "/Conformio/" + cr.dbname

        # check user permissions to sync folder!!!

        d = dp.browse(cr, SUPERUSER_ID, ids, context={})
        f_path = '/'
        for node in dp.build_folder_path(cr, uid, ids):
            f_path = '/' + node.name + f_path

        f_path = f_path_prefix + f_path

        s_path = f_path.rstrip('/')
        print(s_path)

        drop_files = []
        drop_folders = []
        try:
            flr = dbx.files_list_folder(s_path)
        except dropbox.exceptions.ApiError as err:
            print('Folder listing failed for', s_path, '-- assumped empty:', err)
        else:
            if flr:
                # get dropbox folders
                for entry in flr.entries:
                    print(entry.name)
                    print(entry)
                    if hasattr(entry, 'client_modified'):
                        drop_files.append(entry)
                    else:
                        drop_folders.append(entry)

        ap = self.pool['ir.attachment']
        file_id = ap.search(cr, uid, [('parent_id', '=', d.id), ('file_active', '=', True)])
        files = ap.browse(cr, uid, file_id, context={})

        def fs(self, cr):
            return tools.config.filestore(cr.dbname)

        path = ''
        full_path = ''
        for file in files:
            found = False

            # extract file path
            path = file.store_fname
            path = re.sub('[.]', '', path)
            path = path.strip('/\\')
            full_path = os.path.join(fs(self, cr), path)
            l_full_path = (f_path + file.name).lower()
            print (l_full_path)
            for item in drop_files:
                if item.path_lower == l_full_path:  # we found file on dropbox, compare dates and sizes
                    mtime = os.path.getmtime(full_path)
                    mtime_dt = datetime.datetime(*time.gmtime(mtime)[:6])
                    size = os.path.getsize(full_path)
                    if mtime_dt == item.client_modified and size == item.size:
                        print('No change')
                    else:
                        print('Change!')
                        print(mtime_dt)
                        print(item.client_modified)
                        if mtime_dt >= item.client_modified:
                            print ('upload')
                            with open(full_path, 'rb') as f:
                                data = f.read()
                            dbx.files_upload(
                                data, f_path + file.name, dropbox.files.WriteMode.overwrite,
                                client_modified=datetime.datetime(*time.gmtime(mtime)[:6]),
                                mute=True)
                        else:
                            print ('download')
                            md, res = dbx.files_download(l_full_path)
                            new_file_content = base64.b64encode(res.content)
                            iap.update_existing_attachment(cr, uid, file.id, new_file_content, item.client_modified,
                                                           full_path)
                    found = True
            if not found:
                # open file
                try:
                    with open(full_path, 'rb') as f:
                        data = f.read()
                    # upload it to dropbox
                    mtime = os.path.getmtime(full_path)
                    # dbx.files_upload(f, f_path + file.name)
                    dbx.files_upload(
                        data, f_path + file.name, dropbox.files.WriteMode.overwrite,
                        client_modified=datetime.datetime(*time.gmtime(mtime)[:6]),
                        mute=True)
                except:
                    print ('Fail')

        # get missing files from dropbox
        for item in drop_files:
            found = False
            for file in files:
                # extract file path
                path = file.store_fname
                path = re.sub('[.]', '', path)
                path = path.strip('/\\')
                full_path = os.path.join(fs(self, cr), path)
                l_full_path = (f_path + file.name).lower()
                if item.path_lower == l_full_path:
                    found = True
            if not found:
                md, res = dbx.files_download(item.path_lower)
                new_file_content = base64.b64encode(res.content)
                iap.insert_new_attachment(cr, uid, d.id, md.name, new_file_content)

        sub_folders = []
        # find child folders in Odoo
        dss = dp.search(cr, uid, [('parent_id', '=', d.id)])
        for folder in dss:
            sub_folders.append(dp.browse(cr, uid, folder, context={}))

        # get missing folders from dropbox
        for item in drop_folders:
            found = False
            for _fld in sub_folders:
                if _fld.name.lower() == item.name.lower():
                    found = True
            if not found:
                dp.create(cr, uid, {'name': item.name, 'parent_id': d.id, 'type': 'directory', 'directory_active': True,
                                    'ressource_id': d.ressource_id})
        d = dp.search(cr, uid, [('parent_id', '=', d.id)])
        for folder in d:
            self.sync_loop(cr, uid, dbx, folder)

    def sync_t(self, cr, uid, t, ids):
        """This method will be called as cron job.
        Gets current Dropbox user and calls "sync_loop" method.
        """

        print uid
        print t
        print ids
        if t:
            dbx = dropbox.Dropbox(t)
            try:
                dbx.users_get_current_account()
            except AuthError as err:
                sys.exit(
                    "ERROR: Invalid access token; try re-generating an access token from the app console on the web.")
            self.sync_loop(cr, uid, dbx, ids)

    def sync(self, cr, uid, ids):
        """Called from client side (via javascript) to start syncing of particular folder (ids).
        If Dropbox token is not given for current user, first we obtain one ny allowing Odoo/Dropbox application to access
        users Dropbox account. Given token is then copy/pasted in user preferences.

        After obtaining Dropbox token, we create new cron job that will continue to sync that folder every minute.

        After that user is added to 'followers' of given folder and 'sync_loop' is invoked to perform actual sync.
        """

        # get current user
        u = self.pool['res.users'].browse(cr, SUPERUSER_ID, uid, context={})

        TOKEN = u.dropbox_token
        if TOKEN:
            print "TOKEN len"
            print len(TOKEN)
        if not TOKEN:
            auth_code = u.dropbox_auth_code
            print (auth_code)
            if auth_code:
                auth_code = auth_code.strip()
                APP_KEY = self.pool['ir.config_parameter'].get_param(cr, SUPERUSER_ID,
                                                                     'epps.dropbox_app_key')
                APP_SECRET = self.pool['ir.config_parameter'].get_param(cr, SUPERUSER_ID,
                                                                        'epps.dropbox_app_secret')
                auth_flow = DropboxOAuth2FlowNoRedirect(APP_KEY, APP_SECRET)

                authorize_url = auth_flow.start()
                try:
                    access_token, user_id = auth_flow.finish(auth_code)
                except dbrest.ErrorResponse, e:
                    print('Error: %s' % (e,))
                    return

                self.pool['res.users'].write(cr, SUPERUSER_ID, uid,
                                             {'dropbox_token': access_token}, context={})
                TOKEN = access_token


        # get values from user

        if TOKEN:
            dbx = dropbox.Dropbox(TOKEN)

            # Check that the access token is valid
            try:
                dbx.users_get_current_account()
            except AuthError as err:
                sys.exit(
                    "ERROR: Invalid access token; try re-generating an access token from the app console on the web.")

            _args = repr([TOKEN, ids])

            # create new cron job if it doesn't exist already
            cid = self.pool['ir.cron'].search(cr, SUPERUSER_ID, [('function', '=', 'sync_t'), ('args', '=', _args),
                                                                 ('model', '=', 'dropbox.integration')])
            if not cid:
                self.pool['ir.cron'].create(cr, SUPERUSER_ID, {
                    'name': 'Sync folder with Dropbox',
                    'interval_type': 'minutes',
                    'numbercall': -1,
                    'user_id': uid,
                    'model': 'dropbox.integration',
                    'function': 'sync_t',
                    'args': _args
                })

            # follow folder if syncing
            Followers = self.pool['mail.followers']
            User = self.pool['res.users']
            user = User.browse(cr, SUPERUSER_ID, uid, context=None)
            fo_ids = Followers.search(cr, SUPERUSER_ID, [('res_model', '=', 'document.directory'),
                                                         ('partner_id', '=', user.partner_id.id), ('res_id', '=', ids)],
                                      context=None)
            if not fo_ids:
                Followers.create(cr, SUPERUSER_ID, {
                    'res_model': 'document.directory',
                    'partner_id': user.partner_id.id,
                    'res_id': ids,
                })
            self.sync_loop(cr, uid, dbx, ids)
        return 0




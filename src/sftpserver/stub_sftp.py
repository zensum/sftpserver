# Copyright (C) 2003-2009  Robey Pointer <robeypointer@gmail.com>
#
# This file is part of paramiko.
#
# Paramiko is free software; you can redistribute it and/or modify it under the
# terms of the GNU Lesser General Public License as published by the Free
# Software Foundation; either version 2.1 of the License, or (at your option)
# any later version.
#
# Paramiko is distrubuted in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Paramiko; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA.

"""
A stub SFTP server for loopback SFTP testing.
"""

import os
from paramiko import ServerInterface, SFTPServerInterface, SFTPServer, SFTPAttributes, \
    SFTPHandle, SFTP_OK, AUTH_SUCCESSFUL, AUTH_FAILED, OPEN_SUCCEEDED, SFTP_PERMISSION_DENIED, SFTP_NO_SUCH_FILE, AUTH_FAILED
from google.cloud import storage
import time
import logging
from io import BytesIO

logging.basicConfig(level=logging.INFO)

PROJECT_ID = os.environ["GCP_PROJECT_ID"]
BUCKET = os.environ["GCP_STORAGE_BUCKET"]

SFTP_PUBLIC_KEY = os.environ.get("SFTP_PUBLIC_KEY", None)
SFTP_USERNAME = os.environ["SFTP_USERNAME"]
SFTP_PASSWORD = os.environ.get("SFTP_PASSWORD", None)

DELETED_META_KEY = "se.zensum.sftpserver/deleted"

def get_storage_client():
    return storage.Client(project=PROJECT_ID)

class StubServer (ServerInterface):
    def check_auth_password(self, username, password):
        if not SFTP_PASSWORD:
            return AUTH_FAILED

        if username != SFTP_USERNAME:
            return AUTH_FAILED

        if password != SFTP_PASSWORD:
            return AUTH_FAILED

        # all are allowed
        return AUTH_SUCCESSFUL

    def check_auth_publickey(self, username, key):
        # all are allowed
        if username != SFTP_USERNAME:
            return AUTH_FAILED

        if key != SFTP_PUBLIC_KEY:
            return AUTH_FAILED

        return AUTH_SUCCESSFUL

    def check_channel_request(self, kind, chanid):
        return OPEN_SUCCEEDED

    def get_allowed_auths(self, username):
        """List availble auth mechanisms."""
        return "password,publickey"


class StubSFTPHandle (SFTPHandle):
    def stat(self):
        return blob_to_stat(self.get_file(self.filename))

    def chattr(self, attr):
        return SFTP_PERMISSION_DENIED

def blob_to_stat(blob):
    attr = SFTPAttributes()
    attr.filename = blob.name
    attr.st_size = blob.size
    attr.st_mode = 0o0100444
    attr.st_uid = 1000
    attr.st_gid = 1000
    ts = blob.time_created.timestamp()
    attr.st_ctime = ts
    attr.st_mtime = blob.updated.timestamp() if blob.updated else ts
    attr.st_atime = blob.updated.timestamp() if blob.updated else ts
    return attr

class StubSFTPServer (SFTPServerInterface):
    # assume current folder is a fine root
    # (the tests always create and eventualy delete a subfolder, so there shouldn't be any mess)
    ROOT = os.getcwd()

    def __init__(self, *args, **kwargs):
        self.client = get_storage_client()
        self.bucket = self.client.get_bucket(BUCKET)
        if self.bucket is None:
            raise RuntimeError("Missing bucket")
        super().__init__(*args, **kwargs)

    def get_file(self, fname):
        print(fname.strip("/"))
        return self.bucket.get_blob(fname.strip("/"))

    def _realpath(self, path):
        return self.ROOT + self.canonicalize(path)


    def list_folder(self, path):
        prefix = path if path != "/" else None
        res = self.bucket.list_blobs(prefix=prefix, max_results=1000, delimiter="/")
        return [blob_to_stat(blob)
                for blob in res
                if not (blob.metadata and blob.metadata.get(DELETED_META_KEY, False) == "1")]


    def stat(self, path):
        try:
            blob = self.get_file(path)
            return blob_to_stat(blob)
        except ex:
            print(ex)
            raise

    def lstat(self, path):
        try:
            blob = self.get_file(path)
            return blob_to_stat(blob)
        except ex:
            print(ex)
            raise

    def open(self, path, flags, attr):
        # Writing is not supported
        bfr = BytesIO()

        blob = self.get_file(path.strip("/"))
        if blob is None:
            return SFTP_NO_SUCH_FILE

        blob.download_to_file(bfr)
        bfr.seek(0)
        fobj = StubSFTPHandle(flags)
        fobj.get_file = self.get_file
        fobj.filename = path
        fobj.readfile = bfr
        fobj.writefile = None
        return fobj

    def remove(self, path):
        blob = self.get_file(path)
        if blob:
            md = blob.metadata
            if md is None:
                md = {}
            md[DELETED_META_KEY] = "1"
            blob.metadata = md
            blob.patch()
        return SFTP_OK

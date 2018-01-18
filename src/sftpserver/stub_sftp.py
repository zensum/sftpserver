# Copyright (C) 2018 Zensum AB <dev@zensum.se>
# Copyright (C) 2003-2009  Robey Pointer <robeypointer@gmail.com>
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

import os
from paramiko import ServerInterface, SFTPServerInterface, SFTPServer, SFTPAttributes, \
    SFTPHandle, SFTP_OK, AUTH_SUCCESSFUL, AUTH_FAILED, OPEN_SUCCEEDED, SFTP_PERMISSION_DENIED, SFTP_NO_SUCH_FILE, AUTH_FAILED, \
    RSAKey
from paramiko.py3compat import decodebytes,b

from google.cloud import storage
import time
import logging
from io import BytesIO

logging.basicConfig(level=logging.DEBUG)

PROJECT_ID = os.environ["GCP_PROJECT_ID"]
BUCKET = os.environ["GCP_STORAGE_BUCKET"]

SFTP_PUBLIC_KEY_PATH = os.environ.get("SFTP_PUBLIC_KEY_PATH", None)
SFTP_USERNAME = os.environ["SFTP_USERNAME"]
SFTP_PASSWORD = os.environ.get("SFTP_PASSWORD", None)

DELETED_META_KEY = "se.zensum.sftpserver/deleted"

def read_authorized_keys(path):
    return (
        parse_pubkey(l)
        for l in open(path, "r")
        if l.strip()
    )

def parse_pubkey(line):
    data = line.strip().split(" ")[1]
    return RSAKey(data=decodebytes(b(data)))

authorized_keys = list(read_authorized_keys(SFTP_PUBLIC_KEY_PATH))

def get_storage_client():
    return storage.Client(project=PROJECT_ID)

class StubServer (ServerInterface):
    def check_auth_password(self, username, password):
        if not SFTP_PASSWORD:
            return AUTH_FAILED

        if username != SFTP_USERNAME or password != SFTP_PASSWORD:
            return AUTH_FAILED

        return AUTH_SUCCESSFUL

    def check_auth_publickey(self, username, key):
        if username != SFTP_USERNAME:
            return AUTH_FAILED
        key_matches = any(k == key for k in authorized_keys)
        if key_matches:
            return AUTH_SUCCESSFUL
        else:
            return AUTH_FAILED

    def check_channel_request(self, kind, chanid):
        return OPEN_SUCCEEDED

    def get_allowed_auths(self, username):
        """List availble auth mechanisms."""
        return "password,publickey"


class StubSFTPHandle (SFTPHandle):
    def stat(self):
        return blob_to_stat(self.blob)

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


def is_blob_deleted(blob):
    return (
        blob.metadata and
        blob.metadata.get(DELETED_META_KEY, False) == "1"
    )


def load_blob_to_bfr(blob):
    bfr = BytesIO()
    blob.download_to_file(bfr)
    bfr.seek(0)
    return bfr


def create_handle(blob, flags):
    fobj = StubSFTPHandle(flags)
    fobj.blob = blob
    fobj.filename = blob.path
    fobj.readfile = load_blob_to_bfr(blob)
    fobj.writefile = None
    return fobj


def mark_as_deleted(blob):
    if not blob:
        return SFTP_NO_SUCH_FILE
    md = blob.metadata
    if md is None:
        md = {}

    if md[DELETED_META_KEY] == "1":
        return False

    md[DELETED_META_KEY] = "1"
    blob.metadata = md
    blob.patch()
    return True


class StubSFTPServer (SFTPServerInterface):
    def __init__(self, *args, **kwargs):
        self.client = get_storage_client()
        self.bucket = self.client.get_bucket(BUCKET)
        if self.bucket is None:
            raise RuntimeError("Missing bucket")
        super().__init__(*args, **kwargs)

    def get_file(self, fname):
        return self.bucket.get_blob(fname.strip("/"))

    def list_folder(self, path):
        prefix = path if path != "/" else None
        res = self.bucket.list_blobs(
            prefix=prefix, max_results=1000, delimiter="/")
        return [blob_to_stat(blob)
                for blob in res if not is_blob_deleted(blob)]

    def stat(self, path):
        blob = self.get_file(path)
        return blob_to_stat(blob)

    def lstat(self, path):
        blob = self.get_file(path)
        return blob_to_stat(blob)

    def open(self, path, flags, attr):
        # Writing is not supported
        blob = self.get_file(path)
        if blob is None:
            return SFTP_NO_SUCH_FILE

        return create_handle(blob, flags)

    def remove(self, path):
        blob = self.get_file(path)
        if blob is None:
            return SFTP_NO_SUCH_FILE

        if mark_as_deleted(blob):
            return SFTP_OK
        else:
            return SFTP_NO_SUCH_FILE

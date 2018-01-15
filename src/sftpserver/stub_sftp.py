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
    SFTPHandle, SFTP_OK, AUTH_SUCCESSFUL, OPEN_SUCCEEDED, SFTP_PERMISSION_DENIED, SFTP_NO_SUCH_FILE
from google.cloud import storage
from io import BytesIO

PROJECT_ID = os.environ["GCP_PROJECT_ID"]
BUCKET = os.environ["GCP_STORAGE_BUCKET"]

def get_storage_client():
    return storage.Client(project=PROJECT_ID)

class StubServer (ServerInterface):
    def check_auth_password(self, username, password):
        # all are allowed
        return AUTH_SUCCESSFUL

    def check_auth_publickey(self, username, key):
        # all are allowed
        return AUTH_SUCCESSFUL

    def check_channel_request(self, kind, chanid):
        return OPEN_SUCCEEDED

    def get_allowed_auths(self, username):
        """List availble auth mechanisms."""
        return "password,publickey"


class StubSFTPHandle (SFTPHandle):
    def stat(self):
        try:
            return SFTPAttributes.from_stat(os.fstat(self.readfile.fileno()))
        except OSError as e:
            return SFTPServer.convert_errno(e.errno)

    def chattr(self, attr):
        return SFTP_PERMISSION_DENIED

def blob_to_stat(blob):
    attr = SFTPAttributes()
    attr.filename = blob.name
    attr.st_size = blob.size
    attr.st_mode = 0o0100444
    attr.st_uid = 1000
    attr.st_gid = 1000
    attr.st_ctime = blob.time_created
    attr.st_mtime = 1
    attr.st_atime = 1
    print(attr)
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

    def get_file(fname):
        print(fname.strip("/"))
        return self.bucket.get_blob(fname.strip("/"))

    def _realpath(self, path):
        return self.ROOT + self.canonicalize(path)


    def list_folder(self, path):
        res = self.bucket.list_blobs(prefix=path if path != "/" else None, max_results=1000, delimiter="/")
        return [blob_to_stat(blob) for blob in res]


    def stat(self, path):
        print("stat {}".format(path))
        try:
            blob = self.get_file(path)
            return blob_to_stat(blob)
        except ex:
            print(ex)

    def lstat(self, path):
        print("stat {}".format(path))
        try:
            blob = self.get_file(path)
            print(blob)
            return blob_to_stat(blob)
        except ex:
            print(ex)

    def open(self, path, flags, attr):
        # Writing is not supported
        print("rheep", path)
        print(flags)
        print(attr)
        bfr = BytesIO()

        blob = self.get_file(path.strip("/"))
        print("wheep")
        if blob is None:
            return SFTP_NO_SUCH_FILE

        blob.download_to_file(bfr)

        bfr.seek(0)

        fobj = StubSFTPHandle(flags)
        fobj.filename = path
        fobj.readfile = bfr
        fobj.writefile = None
        return fobj

    def remove(self, path):
        # TODO: this needs handling
        return SFTP_OK

    def rename(self, oldpath, newpath):
        return SFTP_PERMISSION_DENIED

    def mkdir(self, path, attr):
        return SFTP_PERMISSION_DENIED

    def rmdir(self, path):
        # May not remove directories
        return SFTP_PERMISSION_DENIED

    def chattr(self, path, attr):
        # Not allowed to change permissions
        return SFTP_PERMISSION_DENIED

    def symlink(self, target_path, path):
        # Can't create symlinks
        return SFTP_PERMISSION_DENIED

    def readlink(self, path):
        return SFTP_PERMISSIONED_DENIED

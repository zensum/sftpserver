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
from sftpserver.storage import StorageEngine
import time
import logging
from io import BytesIO

logging.basicConfig(level=logging.DEBUG)

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

class StorageHandle(SFTPHandle):
    def stat(self):
        return blob_to_stat(self.blob)

    def chattr(self, attr):
        return SFTP_PERMISSION_DENIED

def create_handle(path, bfr, flags):
    fobj = StorageHandle(flags)
    fobj.blob = blob
    fobj.filename = path
    fobj.readfile = bfr
    fobj.writefile = None
    return fobj


class StubSFTPServer (SFTPServerInterface):
    def __init__(self, *args, **kwargs):
        self.storage = StorageEngine()
        super().__init__(*args, **kwargs)

    def list_folder(self, path):
        return [blob_to_stat(blob)
                for blob in self.storage.list_folder(path)]

    def stat(self, path):
        return blob_to_stat(self.storage.get_file(path))

    def lstat(self, path):
        return self.stat(path)

    def open(self, path, flags, attr):
        # Writing is not supported
        path, bfr = self.storage.get_path_and_buffer(path)
        if path is None or bfr is None:
            return SFTP_NO_SUCH_FILE

        return create_handle(path, bfr, flags)

    def remove(self, path):
        if self.storage.delete(path):
            return SFTP_OK
        else:
            return SFTP_NO_SUCH_FILE

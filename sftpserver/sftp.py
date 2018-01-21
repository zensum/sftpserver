import os
from paramiko import SFTPServerInterface, SFTPAttributes, \
    SFTPHandle, SFTP_OK, SFTP_PERMISSION_DENIED, SFTP_NO_SUCH_FILE
from sftpserver.storage import StorageEngine


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


def create_handle(path, bfr, flags):
    fobj = StorageHandle(flags)
    fobj.filename = path
    fobj.readfile = bfr
    fobj.writefile = None
    return fobj


class StorageHandle(SFTPHandle):
    def stat(self):
        return blob_to_stat(self.blob)

    def chattr(self, attr):
        return SFTP_PERMISSION_DENIED


class SFTP(SFTPServerInterface):
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

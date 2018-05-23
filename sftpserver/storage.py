from google.cloud import storage
from io import BytesIO
import sftpserver.config as cfg
from itertools import chain
from collections import namedtuple
DELETED_META_KEY = "se.zensum.sftpserver/deleted"

DuckTime=namedtuple("DuckTime",["timestamp"])
duckNever=DuckTime(lambda :0)
class DirectoryBlob:
    """Google storage does not reeeeaalllyy have a concept of directories
    This class emulates enough of the gstorage interface to be statable.
    """
    def __init__(s,prefix,name):
        s.metadata = False
        s.name = (prefix or "" + name).rstrip("/")
        s.size = 0
        s.time_created = duckNever
        s.updated = duckNever
        s.is_dir=True

def get_storage_client():
    return storage.Client(project=cfg.gcp.project_id)


def is_blob_deleted(blob):
    return (
        hasattr(blob, "metadata") and (
        blob.metadata and
        blob.metadata.get(DELETED_META_KEY, False) == "1")
    )


def load_blob_to_bfr(blob):
    bfr = BytesIO()
    blob.download_to_file(bfr)
    bfr.seek(0)
    return bfr


def mark_as_deleted(blob):
    if not blob:
        return False
    md = blob.metadata
    if md is None:
        md = {}

    if is_blob_deleted(blob):
        return False

    md[DELETED_META_KEY] = "1"
    blob.metadata = md
    blob.patch()
    return True


class StorageEngine(object):
    def __init__(self):
        self.client = get_storage_client()
        self.bucket = self.client.get_bucket(cfg.gcp.storage_bucket)
        if self.bucket is None:
            raise RuntimeError("Missing bucket")

    def get_file(self, fname):
        if fname.endswith("/"):
            path = fname.rsplit("/",1)
            return DirectoryBlob(*path)
        return self.bucket.get_blob(fname.strip("/"))

    def list_folder(self, path):
        prefix = path.rstrip("/")+"/" if path != "/" else None
        res = self.bucket.list_blobs(
            prefix=prefix,
            max_results=1000,
            delimiter="/"
        )
        # all the directories are in
        #res.prefixes
        reified_res = list(res) #reading res has side effects needed for the next line, sorry..
        directories = [DirectoryBlob(prefix,i) for i in res.prefixes]
        return (x for x in chain(directories, reified_res) if not is_blob_deleted(x) and x.name and x.name != prefix)

    def get_path_and_buffer(self, fname):
        f = self.get_file(fname)
        if f is not None:
            return (f.path, load_blob_to_bfr(f))
        else:
            return (None, None)

    def delete(self, fname):
        return mark_as_deleted(self.get_file(fname))

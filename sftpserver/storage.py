from google.cloud import storage
from io import BytesIO
import sftpserver.config as cfg

DELETED_META_KEY = "se.zensum.sftpserver/deleted"


def get_storage_client():
    return storage.Client(project=cfg.gcp.project_id)


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
        return self.bucket.get_blob(fname.strip("/"))

    def list_folder(self, path):
        prefix = path if path != "/" else None
        res = self.bucket.list_blobs(
            prefix=prefix,
            max_results=1000,
            delimiter="/"
        )
        return (x for x in res if not is_blob_deleted(x))

    def get_path_and_buffer(self, fname):
        f = self.get_file(fname)
        if f is not None:
            return (f.path, load_blob_to_bfr(f))
        else:
            return (None, None)

    def delete(self, fname):
        return mark_as_deleted(self.get_file(fname))

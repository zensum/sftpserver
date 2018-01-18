import os
from paramiko import RSAKey, ServerInterface
from paramiko.py3compat import b, decodebytes

SFTP_PUBLIC_KEY_PATH = os.environ.get("SFTP_PUBLIC_KEY_PATH", None)
SFTP_USERNAME = os.environ["SFTP_USERNAME"]
SFTP_PASSWORD = os.environ.get("SFTP_PASSWORD", None)

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

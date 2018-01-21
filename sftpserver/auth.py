from paramiko import (RSAKey, ServerInterface,
                      AUTH_SUCCESSFUL, AUTH_FAILED,
                      OPEN_SUCCEEDED)
from paramiko.py3compat import b, decodebytes
import sftpserver.config as cfg


def read_authorized_keys(path):
    return (
        parse_pubkey(l)
        for l in open(path, "r")
        if l.strip()
    )


def parse_pubkey(line):
    data = line.strip().split(" ")[1]
    return RSAKey(data=decodebytes(b(data)))


class CustomServer(ServerInterface):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        key_path = cfg.auth.authorized_keys_path
        self.username = cfg.auth.username
        self.password = cfg.auth.password
        if key_path is None:
            self.authorized_keys = set()
        else:
            self.authorized_keys = set(read_authorized_keys(key_path))

    def check_auth_password(self, username, password):
        if not self.password:
            return AUTH_FAILED

        if username != self.username or password != self.password:
            return AUTH_FAILED

        return AUTH_SUCCESSFUL

    def check_auth_publickey(self, username, key):
        if username != self.username:
            return AUTH_FAILED

        if key in self.authorized_keys:
            return AUTH_SUCCESSFUL
        else:
            return AUTH_FAILED

    def check_channel_request(self, kind, chanid):
        return OPEN_SUCCEEDED

    def get_allowed_auths(self, username):
        """List availble auth mechanisms."""
        if len(self.authorized_keys):
            return "password,publickey"
        else:
            return "password"

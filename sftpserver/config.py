import toml
import os


CURRENT_DIR = os.path.dirname(__file__)
DEFAULTS_CONFIG = os.path.join(CURRENT_DIR, "defaults.toml")

USER_CONFIG_PATH = os.environ.get("CONFIG_PATH", "/etc/config/sftpserver.toml")
CONFIG_PATHS = [USER_CONFIG_PATH, DEFAULTS_CONFIG]


def load_config(path):
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return toml.load(f)


def get_path(d, path):
    if d and path[0] in d:
        if len(path) > 1:
            return get_path(d[path[0]], path[1:])
        else:
            return d[path[0]]
    else:
        return None


def get_path_from_configs(configs, path):
    for config in configs:
        res = get_path(config, path)
        if res is not None:
            return res
    return None


class Config(object):
    def __init__(self, settings):
        configs = [load_config(x) for x in CONFIG_PATHS]

        for (name, env, config_path) in settings:
            if env in os.environ and os.environ[env] != "":
                setattr(self, name, os.environ[env])
            else:
                res = get_path_from_configs(configs, config_path)

                setattr(self, name, res)

auth = Config([
    ("authorized_keys_path", "SFTP_PUBLIC_KEY_PATH", ["auth", "authorized_keys_path"]),
    ("username", "SFTP_USERNAME", ["auth", "username"]),
    ("password", "SFTP_PASSWORD", ["auth", "password"]),
])

sftp = Config([
    ("host_key_path", "HOST_KEY_PATH", ["sftp", "host_key_path"]),
    ("port", "PORT", ["sftp", "port"]),
    ("listen_host", "LISTEN_HOST", ["sftp", "listen"])
])

gcp = Config([
    ("project_id", "GCP_PROJECT_ID", ["gcloud", "project_id"]),
    ("storage_bucket", "GCP_STORAGE_BUCKET", ["gcloud", "bucket"]),
])

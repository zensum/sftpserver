import paramiko as pm
import socket
from sftpserver.sftp import SFTP
from sftpserver.auth import CustomServer
import sftpserver.config as cfg
import time
import sys

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("sftpserver")

BACKLOG = 10


def create_listen_socket(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        True
    )
    sock.bind((host, port))
    sock.listen(BACKLOG)
    return sock


def create_transport(conn, host_key):
    t = pm.Transport(conn)
    t.add_server_key(host_key)
    t.set_subsystem_handler(
        'sftp', pm.SFTPServer, SFTP
    )
    return t

chans = []
def server_loop(sock, host_key, server):
    while True:
        conn, addr = sock.accept()
        transport = create_transport(conn, host_key)
        transport.start_server(server=server)
        # Chan is assigned to keep it from being GC'd
        chan = transport.accept()
        chans.append(chan)
        if len(chans) > 100:
            clean_chans()
        time.sleep(.1)

def clean_chans():
    for c in chans[:]:
        try:
            if c.exit_status_ready():
                chans.remove(c)
        except AttributeError:
            pass #Sometimes remove fails due to race-condition, this "solves" it


def main():
    server = CustomServer()
    port = int(cfg.sftp.port)
    sock = create_listen_socket(cfg.sftp.listen_host, port)
    host_key = pm.RSAKey.from_private_key_file(cfg.sftp.host_key_path)

    if cfg.gcp.application_credentials_file == None:
        logging.error("""
        You need to set GCP_APPLICATION_CREDENTIALS_FILE or equivalent 
        generate the file locally by running
        gcloud iam service-accounts keys create sftp_credentials.json --iam-account service_uesr@{}.iam.gserviceaccount.com
        """.format((cfg.gcp.project_id or "example-project")).strip())
        sys.exit(1)

    try:
        open(cfg.gcp.application_credentials_file,"r")
    except:
        logging.error("Could not open credentials file '{}'".format((cfg.gcp.application_credentials_file)))
        sys.exit(1)

    while True:
        try:
            server_loop(sock, host_key, server)
        except (pm.ssh_exception.SSHException,EOFError) as e:
            if not True in ("protocol banner" in i for i in  e.args):
                logger.error("Server exited badly: {}".format(e))


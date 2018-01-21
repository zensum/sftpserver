import paramiko as pm
import socket
from sftpserver.sftp import SFTP
from sftpserver.auth import CustomServer
import sftpserver.config as cfg
import time

import logging
logging.basicConfig(level=logging.DEBUG)

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


def server_loop(sock, host_key, server):
    while True:
        conn, addr = sock.accept()
        transport = create_transport(conn, host_key)
        transport.start_server(server=server)
        # Chan is assigned to keep it from being GC'd
        chan = transport.accept() # noqa
        while transport.is_active():
            time.sleep(1)


def main():
    server = CustomServer()
    port = int(cfg.sftp.port)
    sock = create_listen_socket(cfg.sftp.listen_host, port)
    host_key = pm.RSAKey.from_private_key_file(cfg.sftp.host_key_path)
    server_loop(sock, host_key, server)

import paramiko as pm
import os
import socket
from sftpserver.stub_sftp import StubSFTPServer
from sftpserver.auth import CustomServer
import time

HOST = 'localhost'
PORT = int(os.environ.get("PORT", "3373"))
HOST_KEY_PATH = os.environ["HOST_KEY_PATH"]
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
        'sftp', pm.SFTPServer, StubSFTPServer
    )
    return t

def server_loop(sock, host_key, server):
    while True:
        conn, addr = sock.accept()
        transport = create_transport(conn, host_key)
        transport.start_server(server=server)
        channel = transport.accept()
        while transport.is_active():
            time.sleep(1)

def main():
    server = CustomServer()
    sock = create_listen_socket(HOST, PORT)
    host_key = pm.RSAKey.from_private_key_file(HOST_KEY_PATH)
    server_loop(sock, host_key, server)

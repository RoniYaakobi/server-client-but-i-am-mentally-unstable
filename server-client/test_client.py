import socket
from tcp_by_size import send_with_size, recv_by_size
from show_image_windows_api import ViewBitMapStream

server = socket.socket()

server.connect(("127.0.0.1", 12345))

send_with_size(server, "f")

ViewBitMapStream(sock = server)
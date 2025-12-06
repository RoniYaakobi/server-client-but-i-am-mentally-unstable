import socket
from tcp_by_size import send_with_size, recv_by_size
from screenshot import ScreenCapture


server = socket.socket()

server.bind(("127.0.0.1", 12345))

server.listen(5)

client, _ = server.accept()


while True:
    recv_by_size(client)
    ScreenCapture.take_screenshot(sock= client)

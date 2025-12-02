__author__ = 'Roni'

import os
from tcp_by_size import send_with_size, recv_by_size
from datetime import datetime

MAX_DATA_CHUNK_SIZE = 2**14
FTP_FINISH = b"EnD_0f_Tr@N$$m!$$!0N"


def recv_file(sock, path = r"C:\Users\roniy\Downloads"):
    if not os.path.isfile(path) and os.path.exists(path):
        path = os.path.join(path, datetime.now().strftime("%Y-%m-%d-%H-%M-%S.txt"))

    with open(path, "wb") as f:
        while True:
            chunk = recv_by_size(sock)
            if chunk == FTP_FINISH:
                break
            f.write(chunk)
    return "FTP Success"

    
def send_file(sock, path):
    if not os.path.isfile(path): # Don't try to send folder
        raise FileNotFoundError
    
    with open(path,"rb") as f: # Open the file as binary data
        chunk = f.read(MAX_DATA_CHUNK_SIZE)
        while chunk != b'':
            send_with_size(sock, chunk)
            chunk = f.read(MAX_DATA_CHUNK_SIZE)
    send_with_size(sock, FTP_FINISH)

    return "FTP Success"

import socket
import json


sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind(("0.0.0.0", 9000))
sock.listen(10)
while 1:
    csock, _ = sock.accept()
    with csock:
        csock.settimeout(1)
        try:
            payload = json.loads(csock.recv(2048).decode("utf-8"))
            print(payload)
        except:
            pass
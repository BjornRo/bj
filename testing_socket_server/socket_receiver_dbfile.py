import tarfile
import socket
import io
import ssl

HEADER = 10
UTF8 = "utf-8"
SERVERIP = "192.168.1.199"
PORT = 5050
ADDR = (SERVERIP, PORT)
TOKEN = "1234567890"


def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.connect(ADDR)
    server.settimeout(10)

    buffer = io.BytesIO()
    # Send token
    server.send(TOKEN.encode(UTF8))
    # Filename {name}\n{filebytes}
    try:
        recvfile = server.recv(32).split(b"\n", 1)
        if len(recvfile) == 2:
            filename = recvfile[0].decode()
            buffer.write(recvfile[1])
    except:
        pass
    # Get filebytes
    while True:
        recvfile = server.recv(4096)
        if not recvfile:
            buffer.seek(0)
            savetar_to_file("copy" + filename, buffer)
            break
        buffer.write(recvfile)
    server.close()

def savetar_to_file(filename: str, bdata: bytes):
    with tarfile.open(fileobj=bdata, mode="r:gz") as t:
        tardata = t.extractfile(t.getmembers()[0]).read()
    with open(filename, "wb") as f:
        f.write(tardata)


if __name__ == "__main__":
    main()

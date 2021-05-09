import socket
import tarfile
from io import BytesIO
import ssl

UTF8 = "utf-8"
CLOSE_MSG = "CLOSE"
SERVER = "192.168.1.199"
PORT = 5050
ADDRESS = (SERVER, PORT)
TIMEOUT = 4
TOKEN = "1234567890"

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(ADDRESS)
    server.listen(5)

    # Main loop, can only handle one client at a time.
    for _ in range(4):
        client, _ = server.accept()
        #wrap_client = ssl.wrap_socket(client, server_side=True)
        with client:
            client.settimeout(5) # One sec to send token.
            try:
                if client.recv(len(TOKEN)).decode(UTF8) == TOKEN:
                    with open("main_db.db", "rb") as f:
                        source = BytesIO(f.read())
                    tardb = BytesIO()
                    with tarfile.open(fileobj=tardb, mode="w:gz") as tar:
                        info = tarfile.TarInfo("main_db.db")
                        info.size = source.seek(0, 2)
                        source.seek(0)
                        tar.addfile(info, source)
                    file = tardb.getvalue()
                    client.sendall("main_db.db\n".encode(UTF8) + file)
                    print("File sent")
            except:
                pass
    server.close()

if __name__ == "__main__":
    main()
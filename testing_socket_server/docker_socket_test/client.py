import socket
import json
from datetime import datetime

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.settimeout(1)
    s.connect(("srv", 9000))
    s.sendall(json.dumps(["key", {"data":55}, {"time": datetime.now().isoformat()}]).encode('utf-8'))
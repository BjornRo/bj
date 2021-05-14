from ast import literal_eval
from home_app.remote_docker.sensor_logger.__main__ import TOKEN
import paho.mqtt.client as mqtt
from datetime import datetime
import sqlite3
from threading import Thread, Semaphore
import schedule
from time import sleep
from pymemcache.client.base import PooledClient
import json
#from bmemcached import Client
from configparser import ConfigParser
import socket
import ssl
import sys

# Idea is to keep this as threading and remote_docker/sensor_logger as asyncio
# This is to compare the flavours of concurrency.

# MISC
UTF8 = "utf-8"

# Config reader -- Path(__file__).parent.absolute() /
CFG = ConfigParser()
CFG.read("config.ini")

# SSL Context
HOSTNAME = CFG["CERT"]["url"]
SSLPATH = f"/etc/letsencrypt/live/{HOSTNAME}/"
SSLPATH_TUPLE = (SSLPATH + "fullchain.pem", SSLPATH + "privkey.pem")
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain(*SSLPATH_TUPLE)

# Token for an eventual use
TOKEN = CFG["TOKEN"]["token"]

# Socket info constants.
COMMAND_LEN = 1
DEV_NAME_LEN = int(CFG["TOKEN"]["dev_name_len"])

# Socket setup
S_PORT = 42661

# Datastructure is in the form of:
#  devicename/measurements: for each measurement type: value.
# New value is a flag to know if value has been updated since last SQL-query. -> Each :00, :30
def main():
    main_node_data = {
        "home": {
            "bikeroom/temp": {"Temperature": -99},
            "balcony/temphumid": {"Temperature": -99, "Humidity": -99},
            "kitchen/temphumidpress": {"Temperature": -99, "Humidity": -99, "Airpressure": -99},
        }
    }
    device_login = {}
    # Read data file. Adds the info for remote devices.
    with open("remotedata.json", "r") as f:
        for mainkey, mainvalue in json.loads(f.read()).items():
            device_login[mainkey] = mainvalue.pop("password")
            main_node_data[mainkey] = mainvalue

    # Associated dict to see if the values has been updated. This is to let remote nodes
    # just send data and then you can decide at the main node.
    main_node_new_values = {
        sub_node: {device: False for device in sub_node_data}
        for sub_node, sub_node_data in main_node_data.items()
    }

    # Setup memcache and set initial values for memcached.
    class JSerde(object):
        def serialize(self, key, value):
            return json.dumps(value), 2

    memcache_local = PooledClient("memcached:11211", serde=JSerde(), max_pool_size=3)
    for key in main_node_data.keys():
        memcache_local.set("weather_data_" + key, main_node_data[key])

    # Semaphores to stop race conditions due to threading.
    # Each node gets its "own" semaphore since the nodes don't interfere with eachother
    # Before SQL Queries, all locks are acquired since this is a read/write situation.
    lock = Semaphore(len(main_node_data))
    Thread(
        target=mqtt_agent,
        args=(
            main_node_data["home"],
            main_node_new_values["home"],
            memcache_local,
            lock,
        ),
        daemon=True,
    ).start()
    # Thread(
    #     target=remote_fetcher,
    #     args=(
    #         main_node_data["remote_sh"],
    #         main_node_new_values["remote_sh"],
    #         memcache_local,
    #         "remote_sh",
    #         lock,
    #     ),
    #     daemon=True,
    # ).start()
    Thread(
        target=data_socket,
        args=(
            main_node_data,
            main_node_new_values,
            device_login,
            memcache_local,
            lock,
        ),
        daemon=True,
    ).start()
    schedule_setup(main_node_data, main_node_new_values, lock)

    # Poll tmpdata until all Nones are gone.
    while 1:
        sleep(1)
        for sub_node_values in main_node_data["home"].values():
            if -99 in sub_node_values.values():
                break
        else:
            break

    while 1:
        schedule.run_pending()
        sleep(10)


def data_socket(main_node_data, main_node_new_values, device_login, mc_local, lock):
    time_last_update = {
        sub_node: {device: datetime.min for device in sub_node_data}
        for sub_node, sub_node_data in main_node_data.items()
        if sub_node != "home"
    }
    keys = ("Temperature", "Humidity", "Airpressure")

    def client_handler(client: ssl.SSLSocket):
        # No need for contex-manager due to finally force close clause in parent.
        try:
            client.settimeout(5)
            # Get device name. Send devicename and password in one.
            device_name = client.recv(DEV_NAME_LEN).decode(UTF8)
            # Check if password is ok, else throw keyerror or return.
            passw = device_login[device_name].encode(UTF8)
            if client.recv(len(passw)) != passw:
                return
            # Notify that it is ok to send data now. Change timeout to keep connection alive.
            client.settimeout(60)
            client.send(b"OK")
            # While connection is alive, send data. If connection is lost, then an
            # exception may be thrown and the while loop exits, and thread is destroyed.
            while 1:
                # Structure: {sub_device_name: [time, {data}]} or {sub_device_name: [time, [data]]}
                recvdata = client.recv(512)
                # If data is empty, client disconnected.
                if not recvdata:
                    break
                payload = json.loads(recvdata.decode(UTF8))
                # Will throw exception if payload isn't a dict.
                for device_key, (time, data) in payload.items():
                    try:
                        # Test if time is valid.
                        dt_time = datetime.fromisoformat(time)
                    except:
                        continue
                    if time_last_update[device_name][device_key] >= dt_time:
                        continue
                    if isinstance(data, dict):
                        if data.keys() != main_node_data[device_name][device_key].keys():
                            continue
                        data_generator = data.items()
                    elif isinstance(data, list):
                        if len(data) != len(main_node_data[device_name][device_key]):
                            continue
                        data_generator = zip(keys, data)
                    else:
                        # If data is not in iter_format.
                        continue
                    tmpdata = {}
                    for data_key, value in data_generator:
                        if not _test_value(data_key, value, 100):
                            break
                        tmpdata[data_key] = value
                    else:
                        with lock:
                            main_node_data[device_name][device_key].update(tmpdata)
                            main_node_new_values[device_name][device_key] = True
                        time_last_update[device_name][device_key] = dt_time
                timedata = {k: v.isoformat() for k, v in time_last_update[device_name].items()}
                mc_local.set("weather_data_" + device_name + "_time", timedata)
                mc_local.set("weather_data_" + device_name, main_node_data[device_name])
        except Exception as e:
            print(e, file=sys.stderr)
        finally:
            try:
                client.close()
            except:
                pass

    with socket.socket(socket.AF_INET6, socket.SOCK_STREAM) as srv:
        srv.bind(("", S_PORT))
        srv.listen(10)
        with context.wrap_socket(srv, server_side=True) as sslsrv:
            while 1:
                try:
                    client = sslsrv.accept()[0]
                    # Spawn a new thread.
                    Thread(target=client_handler, args=(client,), daemon=True).start()
                except:
                    pass

"""
def remote_fetcher(sub_node_data, sub_node_new_values, memcache, remote_key, lock):
    def test_compare_restore(value1, value2):
        # Get the latest value from two sources that may lag or timeout.. woohoo
        # Test every possibility...Try catch to reduce if statements.
        try:
            if value1 is None:
                value = json.loads(value2)
            else:
                if value2 is None:
                    value = json.loads(value1)
                else:
                    value1, value2 = json.loads(value1), json.loads(value2)
                    try:
                        t1 = datetime.fromisoformat(value1.pop(-1))
                        try:
                            t2 = datetime.fromisoformat(value2.pop(-1))
                            return [*value1, t1] if t1 >= t2 else [*value2, t2]
                        except:
                            return [*value1, t1]
                    except:
                        value = value2
                return [*value[:2], datetime.fromisoformat(value[2])]
        except:
            pass
        return None

    memcachier1 = Client((CFG["DATA"]["server"],), CFG["DATA"]["user"], CFG["DATA"]["pass"])
    memcachier2 = Client((CFG["DATA2"]["server"],), CFG["DATA2"]["user"], CFG["DATA2"]["pass"])

    count_error = 0
    last_update_remote = {key: datetime.now() for key in sub_node_data}
    last_update_memcachier = datetime.now()  # Just as init
    while 1:
        sleep(15)
        value = test_compare_restore(memcachier1.get(remote_key), memcachier2.get(remote_key))
        if value is None or value[2] <= last_update_memcachier:
            count_error += 1
            if count_error >= 20:
                # Set to invalid values after n attempts. Reset counter.
                count_error = 0
                with lock:
                    for device, device_data in sub_node_data.items():
                        for key in device_data:
                            sub_node_data[device][key] = -99
                            sub_node_new_values[device] = False
            continue

        # At this point valid value or exception thrown.
        memcache.set("remote_sh_rawdata", (*value[:2], value[2].isoformat()))
        last_update_memcachier = value.pop(-1)
        count_error = 0

        new_sub_node_data, data_time = value
        for device, device_data in new_sub_node_data.items():
            tmpdict = {}
            # Test if new updatetime is newer than last. Otherwise continue.
            try:
                updatetime = datetime.fromisoformat(data_time[device])
            except:
                continue
            if updatetime > last_update_remote[device]:
                for key, value in device_data.items():
                    if key in sub_node_data[device] and _test_value(key, value, 100):
                        tmpdict[key] = value
                    else:
                        break
                else:
                    memcache.set(f"weather_data_{remote_key}", sub_node_data)
                    last_update_remote[device] = updatetime
                    with lock:
                        sub_node_data[device].update(tmpdict)
                        sub_node_new_values[device] = True
"""

# mqtt function does all the heavy lifting sorting out bad data.
def schedule_setup(main_node_data: dict, main_node_new_values: dict, lock: Semaphore):
    db = sqlite3.connect("/db/main_db.db")

    def querydb():
        update_node = [s_node for s_node, nv in main_node_new_values.items() if any(nv.values())]
        if not update_node:
            return

        # Copy data and set values to false.
        time_now = datetime.now().isoformat("T", "minutes")
        new_data = {}
        # Acquire all semaphores
        for _ in range(len(main_node_data)):
            lock.acquire()
        for sub_node in update_node:
            new_data[sub_node] = []
            for device, new_value in main_node_new_values[sub_node].items():
                if new_value:
                    main_node_new_values[sub_node][device] = False
                    new_data[sub_node].append((device, main_node_data[sub_node][device].copy()))
        # Release all semaphores when done.
        lock.release(len(main_node_data))
        cursor = db.cursor()
        cursor.execute(f"INSERT INTO Timestamp VALUES ('{time_now}')")
        for sub_node_data in new_data.values():
            for device, device_data in sub_node_data:
                mkey = device.split("/")[0]
                for table, value in device_data.items():
                    cursor.execute(f"INSERT INTO {table} VALUES ('{mkey}', '{time_now}', {value})")
        db.commit()
        cursor.close()

    def reload_ssl():
        context.load_cert_chain(*SSLPATH_TUPLE)

    # Due to the almost non-existing concurrency, just keep conn alive.
    schedule.every().hour.at(":30").do(querydb)
    schedule.every().hour.at(":00").do(querydb)
    schedule.every().day.at("23:45").do(reload_ssl)


def mqtt_agent(h_tmpdata: dict, h_new_values: dict, memcache, lock):
    def on_connect(client, *_):
        for topic in list(h_tmpdata.keys()) + [status_path]:
            client.subscribe("home/" + topic)

    def on_message(client, userdata, msg):
        # Get values into a listlike form.
        try:
            listlike = literal_eval(msg.payload.decode("utf-8"))
            if isinstance(listlike, dict):
                listlike = tuple(listlike.values())
            elif not (isinstance(listlike, tuple) or isinstance(listlike, list)):
                listlike = (listlike,)
        except:
            return

        # Handle the topic depending on what it is about.
        topic = msg.topic.replace("home/", "")
        if status_path == topic:
            if not set(listlike).difference(set((0, 1))) and len(listlike) == 4:
                memcache.set("relay_status", listlike)
            return

        if len(listlike) != len(h_tmpdata[topic]):
            return

        tmpdict = {}
        for key, value in zip(h_tmpdata[topic].keys(), listlike):
            # If a device sends bad data -> break and discard, else update
            if not _test_value(key, value):
                break
            tmpdict[key] = value / 100
        else:
            memcache.set("weather_data_home", h_tmpdata)
            with lock:
                h_tmpdata[topic].update(tmpdict)
                h_new_values[topic] = True

    # Setup and connect mqtt client. Return client object.
    status_path = "balcony/relay/status"
    client = mqtt.Client("br_logger")
    client.on_connect = on_connect
    client.on_message = on_message
    while True:
        try:
            if client.connect("mqtt", 1883, 60) == 0:
                break
        except:
            pass
        sleep(5)
    client.loop_forever()


def _test_value(key, value, magnitude=1) -> bool:
    try:
        value *= magnitude
        if key == "Temperature":
            return -5000 <= value <= 6000
        elif key == "Humidity":
            return 0 <= value <= 10000
        elif key == "Airpressure":
            return 90000 <= value <= 115000
    except:
        pass
    return False


if __name__ == "__main__":
    main()

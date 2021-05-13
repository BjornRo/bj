from ast import literal_eval
import paho.mqtt.client as mqtt
from datetime import datetime
import sqlite3
from threading import Thread, Lock
import schedule
from time import sleep
from pymemcache.client.base import PooledClient
import json
from bmemcached import Client
from configparser import ConfigParser
from pathlib import Path
import socket

#from multiprocessing import Process
#import pandas as pd
#import numpy as np
#import matplotlib.pyplot as plt


#TODO
# Heavy refactorizing, IF I know that the remote memcache can be deleted. I don't like
# having a 3rd party service as middle man. Local memcache is necessary for flask.
#
# Too convoluted. Some parts should probably go into new containers
# Such as creating graphs etc. DB file can still be accessed from "anywhere".


CFG = ConfigParser()
CFG.read(Path(__file__).parent.absolute() / "config.ini")

# Idea is to keep this as threading and remote_docker/sensor_logger as asyncio
# This is to compare the flavours of concurrency.

# Datastructure is in the form of:
#  devicename/measurements: for each measurement type: value.
# New value is a flag to know if value has been updated since last SQL-query. -> Each :00, :30
def main():
    main_node_data = {
        "home": {
            "bikeroom/temp": {"Temperature": -99},
            "balcony/temphumid": {"Temperature": -99, "Humidity": -99},
            "kitchen/temphumidpress": {
                "Temperature": -99,
                "Humidity": -99,
                "Airpressure": -99,
            },
        },
        "remote_sh": {
            "pizw/temp": {"Temperature": -99},
            "hydrofor/temphumidpress": {
                "Temperature": -99,
                "Humidity": -99,
                "Airpressure": -99,
            },
        },
    }
    # Associated dict to see if the values has been updated. This is to let remote nodes
    # just send data and then you can decide at the main node.
    main_node_new_values = {
        sub_node: {device: False for device in sub_node_data}
        for sub_node, sub_node_data in main_node_data.items()
    }


    # Setup memcache.
    class JSerde(object):
        def serialize(self, key, value):
            return json.dumps(value), 2

    memcache_local = PooledClient("memcached:11211", serde=JSerde(), max_pool_size=3)

    # Set initial values for memcached.
    memcache_local.set("weather_data_home", main_node_data["home"])
    memcache_local.set("weather_data_remote_sh", main_node_data["remote_sh"])

    # Lock to stop race conditions due to threading.
    lock = Lock()
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
    Thread(
        target=remote_fetcher,
        args=(
            main_node_data["remote_sh"],
            main_node_new_values["remote_sh"],
            memcache_local,
            "remote_sh",
            lock
        ),
        daemon=True,
    ).start()
    Thread(
        target=data_socket,
        args=(9000, main_node_data, main_node_new_values),
        daemon=True,
    ).start()
    matplotlib_setup()
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

# TODO
# Implement SSL Socket instead. This is mostly for "future" use for devices that is stuck
# behind a firewall or similar. Dynamic IPv6 which makes the open ports apply for wrong ports if ip change.
def data_socket(main_node_data, main_node_new_values, port=9000):
    timestamps = {
        sub_node: {dev: datetime.now() for dev in sub_node_data}
        for sub_node, sub_node_data in main_node_data.items()
        if sub_node != "home"
    }
    keys = ("Temperature", "Humidity", "Airpressure")
    sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    sock.bind((None, port))
    sock.listen(10)
    while 1:
        csock, _ = sock.accept()
        with csock:
            csock.settimeout(1)
            try:
                # [key, {device_key{measurement_key: data}} or {device_key: [data]}, {device_key: time}]
                # data should have same keys as times.
                key, data, times = json.loads(csock.recv(2048).decode("utf-8"))
                if len(data) != len(times):
                    continue

                for device_key, time in times.items():
                    if isinstance(data[device_key], dict):
                        if main_node_data[key][device_key].keys() != data[device_key].keys():
                            continue
                        data_gen = data[device_key].items()
                    elif isinstance(data[device_key], list):
                        if len(main_node_data[key][device_key]) != len(data[device_key]):
                            continue
                        data_gen = zip(keys, data[device_key])

                    dt_time = datetime.fromisoformat(time)
                    if timestamps[key][device_key] < dt_time:
                        for data_key, value in data_gen:
                            main_node_data[key][device_key][data_key] = value
                            timestamps[key][device_key] = dt_time
                            main_node_new_values[key][device_key] = True
            except:
                pass


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


# mqtt function does all the heavy lifting sorting out bad data.
def schedule_setup(main_node_data: dict, main_node_new_values: dict, lock: Lock):
    def querydb():
        # Check if there exist any values that should be queried. To reduce as much time with lock.
        # update_node = []
        # for sub_node, new_values in main_node_new_values.items():
        #     if any(new_values.values()):
        #         update_node.append(sub_node)
        update_node = [s_node for s_node, nv in main_node_new_values.items() if any(nv.values())]
        if not update_node:
            return

        # Copy data and set values to false.
        time_now = datetime.now().isoformat("T", "minutes")
        new_data = {}
        with lock:
            for sub_node in update_node:
                new_data[sub_node] = []
                for device, new_value in main_node_new_values[sub_node].items():
                    if new_value:
                        main_node_new_values[sub_node][device] = False
                        new_data[sub_node].append((device, main_node_data[sub_node][device].copy()))
        cursor = db.cursor()
        cursor.execute(f"INSERT INTO Timestamp VALUES ('{time_now}')")
        for sub_node_data in new_data.values():
            for device, device_data in sub_node_data:
                mkey = device.split("/")[0]
                for table, value in device_data.items():
                    cursor.execute(f"INSERT INTO {table} VALUES ('{mkey}', '{time_now}', {value})")
        db.commit()
        #cursor.execute(query)
        #data = cursor.fetchall()
        cursor.close()
        #Process(target=create_graphs_in_new_process, args=(data,)).start()

    query = """SELECT t.time, ktemp, khumid, press, btemp, bhumid, brtemp
FROM Timestamp t
LEFT OUTER JOIN
(SELECT time, temperature AS ktemp
FROM Temperature
WHERE measurer = 'kitchen') a ON t.time = a.time
LEFT OUTER JOIN
(SELECT time, humidity As khumid
FROM Humidity
WHERE measurer = 'kitchen') b ON t.time = b.time
LEFT OUTER JOIN
(SELECT time, airpressure AS press
FROM Airpressure
WHERE measurer = 'kitchen') c ON t.time = c.time
LEFT OUTER JOIN
(SELECT time, temperature AS btemp
FROM Temperature
WHERE measurer = 'balcony') d ON t.time = d.time
LEFT OUTER JOIN
(SELECT time, humidity As bhumid
FROM Humidity
WHERE measurer = 'balcony') e ON t.time = e.time
LEFT OUTER JOIN
(SELECT time, temperature AS brtemp
FROM Temperature
WHERE measurer = 'bikeroom') f ON t.time = f.time"""

    # Due to the almost non-existing concurrency, just keep conn alive.
    db = sqlite3.connect("/db/main_db.db")
    schedule.every().hour.at(":30").do(querydb)
    schedule.every().hour.at(":00").do(querydb)


def matplotlib_setup():
    pass


# def create_graphs_in_new_process(data):
#     col = ("date", "ktemp", "khumid", "pressure", "btemp", "bhumid", "brtemp")
#     df = pd.DataFrame(data, columns=col)
#     df["date"] = pd.to_datetime(df["date"])  # format="%Y-%m-%dT%H:%M" isoformat already
#     plt.plot(df["date"][-48 * 21 :], df["brtemp"][-48 * 21 :])
#     plt.plot(df["date"][-48 * 21 :], df["pressure"][-48 * 21 :] - 1000)
#     plt.show()


def mqtt_agent(h_tmpdata: dict, h_new_values: dict, memcache, lock: Lock):
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
            if client.connect("www.home", 1883, 60) == 0:
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

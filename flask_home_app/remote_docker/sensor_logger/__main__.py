from ast import literal_eval
import paho.mqtt.client as mqtt
from datetime import datetime
import time
import json
import glob

from threading import Lock, Thread
import sqlite3
import schedule

from bmemcached import Client
import configparser
import pathlib


# Defined read only global variables
# Find the device file to read from.
device_file = glob.glob("/sys/bus/w1/devices/28*")[0] + "/w1_slave"

# To stop subscribing to non-existing devices.
sub_denylist = ("pizw/temp",)

# Asyncio hurts my head. Program is trying to access a shared resource.
# Only data race is only when DB AND MQTT try to access the resource. We just lock this situation.
lock = Lock()


def main():
    # Datastructure is in the form of:
    #  devicename/measurements: for each measurement type: value.
    # New value is a flag to know if value has been updated since last SQL-query. -> Each :00, :30
    tmpdata = {
        "pizw/temp": {
            "Temperature": -99,
        },
        "hydrofor/temphumidpress": {
            "Temperature": -99,
            "Humidity": -99,
            "Airpressure": -99,
        },
    }
    new_values = {key: False for key in tmpdata}
    last_update = {key: None for key in tmpdata}

    # Memcache setup. Two servers for redundancy
    cfg = configparser.ConfigParser()
    cfg.read(pathlib.Path(__file__).parent.absolute() / "config.ini")
    memcachier1 = Client((cfg["DATA"]["server"],), cfg["DATA"]["user"], cfg["DATA"]["pass"])
    memcachier2 = Client((cfg["DATA2"]["server"],), cfg["DATA2"]["user"], cfg["DATA2"]["pass"])

    # Setup and start mqtt.
    Thread(target=mqtt_agent, args=(tmpdata, new_values, last_update), daemon=True).start()

    # Setup schedule
    schedule_setup(tmpdata, new_values)

    # Slowly poll away -99.
    while 1:
        time.sleep(1)
        read_temp(tmpdata, new_values, "pizw/temp", last_update)
        for value_list in tmpdata.values():
            if -99 in value_list.values():
                break
        else:
            break

    while 1:
        read_temp(tmpdata, new_values, "pizw/temp", last_update)

        # Doesn't matter if race condition. Non-critical values.
        # Check so that all values are new after a SQL query.
        data = json.dumps((tmpdata, last_update, datetime.now().isoformat()))
        memcachier1.set("remote_sh", data)
        memcachier2.set("remote_sh", data)

        schedule.run_pending()
        time.sleep(5)


def schedule_setup(tmpdata: dict, new_values: dict):
    def querydb():
        if any(new_values.values()):
            time_now = datetime.now().isoformat("T", "minutes")
            cursor = db.cursor()
            cursor.execute(f"INSERT INTO Timestamp VALUES ('{time_now}')")
            with lock:
                for location, data in tmpdata.items():
                    if not new_values[location]:
                        continue
                    measurer = location.split("/")[0]
                    for table, value in data.items():
                        cursor.execute(
                            f"INSERT INTO {table} VALUES ('{measurer}', '{time_now}', {value})"
                        )
                        new_values[location] = False
            db.commit()
            cursor.close()

    db = sqlite3.connect("/db/remote_sh.db")
    schedule.every().hour.at(":30").do(querydb)
    schedule.every().hour.at(":00").do(querydb)


def read_temp(tmpdata: dict, new_values: dict, measurer: str, last_update):
    with open(device_file, "r") as f:
        lines = f.readlines()
    if lines[0].strip()[-3:] == "YES":
        equals_pos = lines[1].find("t=")
        if equals_pos != -1 and (tmp_val := lines[1][equals_pos + 2 :][:-1]).isdigit():
            conv_val = round(int(tmp_val) / 1000, 1)
            if _test_value("Temperature", int(conv_val * 100)):
                tmpdata[measurer]["Temperature"] = conv_val
                new_values[measurer] = True
                last_update[measurer] = datetime.now().isoformat()

def mqtt_agent(tmpdata: dict, new_values: dict, last_update):
    def on_connect(client, *_):
        for topic in tmpdata:
            # rightside of in, placeholder for a denylist if needed.
            if topic not in sub_denylist:
                client.subscribe("landet/" + topic)

    def on_message(client, userdata, msg):
        # Get values into a __iter__ form. msg is in bytes
        try:
            # Check if string has ( and ) or [ and ]
            if (msg[0] == 40 and msg[-1] == 41) or (msg[0] == 91 and msg[-1] == 93):
                listlike = tuple(map(int, msg[1:-1].split(b",")))
            # Is a number
            elif msg.isdigit():
                listlike = (int(msg),)
            # Dict
            else:
                listlike = json.loads(msg)
        except: # Unsupported datastructures or invalid values
            return

        # Handle the topic depending on what it is about.
        topic = msg.topic[7:]
        if len(listlike) != len(tmpdata[topic]):
            return

        with lock:
            for key, value in zip(tmpdata[topic], listlike):
                # If a device sends bad data -> break and discard, else update
                if not _test_value(key, value):
                    break
                tmpdata[key] = value / 100
            else:
                new_values[topic] = True
                last_update[topic] = datetime.now().isoformat()

    # Setup and connect mqtt client. Return client object.
    client = mqtt.Client("pi_zero_w")
    client.on_connect = on_connect
    client.on_message = on_message
    while True:
        try:
            if client.connect("192.168.1.200", 1883, 60) == 0:
                break
        except:
            pass
        time.sleep(5)
    client.loop_forever()

def _test_value(key, value) -> bool:
    try:
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

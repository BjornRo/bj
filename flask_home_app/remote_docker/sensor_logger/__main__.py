from ast import literal_eval
import paho.mqtt.client as mqtt
from datetime import datetime
import time
import json
import glob
from threading import Thread

from bmemcached import Client
import configparser
import pathlib

# Let mqtt and other services start.
#time.sleep(60)

device_file = glob.glob("/devices/28*")[0] + "/w1_slave"

# Setup and run. Scheduler queries database every full or half hour. Mqtt queries tempdata to memory.
def main():
    tmpdata = {
        "hydrofor/temphumidpress": {
            "Temp_hydro": -99,
            "Humidity": -99,
            "Airpressure": -99,
        }
    }
    outdoor = -99

    cfg = configparser.ConfigParser()
    cfg.read(pathlib.Path(__file__).parent.absolute() / "config.ini")
    memcachier1 = Client((cfg["DATA"]["server"],), cfg["DATA"]["user"], cfg["DATA"]["pass"])
    memcachier2 = Client((cfg["DATA2"]["server"],), cfg["DATA2"]["user"], cfg["DATA2"]["pass"])

    Thread(target=mqtt_agent, args=(tmpdata,), daemon=True).start()

    while 1:
        time.sleep(1)
        tmp_temp = read_temp()
        outdoor = tmp_temp if -50 <= tmp_temp <= 90 else outdoor
        for value_list in tmpdata.values():
            if -99 in list(value_list.values()) + [outdoor]:
                break
        else:
            break

    while 1:
        tmp_temp = read_temp()
        outdoor = tmp_temp if -50 <= tmp_temp <= 90 else outdoor
        data = json.dumps(
            tmpdata["hydrofor/temphumidpress"]
            | {"Temperature": outdoor}
            | {"Time": datetime.now().isoformat()}
        )
        if not memcachier1.set("remote_sh", data):
            memcachier2.set("remote_sh", data)

        time.sleep(5)


def read_temp_raw():
    with open(device_file, "r") as f:
        return f.readlines()


def read_temp():
    lines = read_temp_raw()
    while lines[0].strip()[-3:] != "YES":
        time.sleep(0.05)
        lines = read_temp_raw()
    equals_pos = lines[1].find("t=")
    if equals_pos != -1:
        temp_string = lines[1][equals_pos + 2 :]
        return round(int(temp_string) / 1000, 1)


def mqtt_agent(tmpdata: dict):
    def on_connect(client, *_):
        for topic in tmpdata:
            client.subscribe("landet/" + topic)

    def on_message(client, userdata, msg):
        topic = msg.topic.replace("landet/", "")
        if topic not in tmpdata:
            return
        # Might redo the function to be more readable. Might taken optimization too far... :)
        try:
            listlike = literal_eval(msg.payload.decode("utf-8"))
            if isinstance(listlike, dict):
                listlike = tuple(listlike.values())
            elif not isinstance(listlike, (tuple, list)):
                return
        except:
            return
        if len(listlike) != len(tmpdata[topic]):
            return
        for key, value in zip(tmpdata[topic].keys(), listlike):
            if not _test_value(key, value):
                continue
            tmpdata[topic][key] = value / 100

    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect("192.168.1.200", 1883, 60)
    client.loop_forever()


def _test_value(key, value) -> bool:
    if isinstance(value, int):
        if key == "Temp_hydro":
            return -5000 <= value <= 5000
        elif key == "Humidity":
            return 0 <= value <= 10000
        elif key == "Airpressure":
            return 90000 <= value <= 115000
    return False


if __name__ == "__main__":
    main()

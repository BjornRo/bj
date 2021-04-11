from ast import literal_eval
import paho.mqtt.client as mqtt
from datetime import datetime
import time
import json

from threading import Lock, Thread
import sqlite3
import schedule

from bmemcached import Client
import configparser
import pathlib

# To stop subscribing to non-existing devices.
sub_denylist = ("pizw/temp",)

def main():
    # Datastructure is in the form of:
    #  devicename/measurements: for each measurement type: value.
    # New value is a flag to know if value has been updated since last SQL-query. -> Each :00, :30
    tmpdata = {
        # "pizw/temp": {
        #     "Temperature": -99,
        # },
        "hydrofor/temphumidpress": {
            "Temperature": -99,
            "Humidity": -99,
            "Airpressure": -99,
        },
    }
    new_values = {key: False for key in tmpdata}

    # Setup and start mqtt.
    Thread(target=mqtt_agent, args=(tmpdata, new_values), daemon=True).start()

    # Setup schedule
    #schedule_setup(tmpdata, new_values)

    # Slowly poll away -99.
    while 1:
        time.sleep(1)
        #read_temp(tmpdata, new_values, "pizw/temp")
        print(new_values)
        print(tmpdata)


def mqtt_agent(tmpdata: dict, new_values: dict):
    def on_connect(client, *_):
        for topic in tmpdata:
            # rightside of in, placeholder for a denylist if needed.
            if topic not in sub_denylist:
                client.subscribe("landet/" + topic)

    def on_message(client, userdata, msg):
        # Get values into a listlike form.
        try:
            listlike = literal_eval(msg.payload.decode("utf-8"))
            if isinstance(listlike, dict):
                listlike = tuple(listlike.values())
            elif not isinstance(listlike, (tuple, list)):
                return
        except:
            return

        # Handle the topic depending on what it is about.
        topic = msg.topic.replace("landet/", "")
        if len(listlike) != len(tmpdata[topic]):
            return

        tmpdict = {}
        for key, value in zip(tmpdata[topic].keys(), listlike):
            # If a device sends bad data -> break and discard, else update
            if not _test_value(key, value):
                break
            tmpdict[key] = value / 100
        else:
            tmpdata[topic].update(tmpdict)
            new_values[topic] = True

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
    if isinstance(value, int):
        if key == "Temperature":
            return -5000 <= value <= 6000
        elif key == "Humidity":
            return 0 <= value <= 10000
        elif key == "Airpressure":
            return 90000 <= value <= 115000
    return False
from ast import literal_eval
import paho.mqtt.client as mqtt
from datetime import datetime
import sqlite3
from threading import Thread, Lock
import schedule
import time
from pymemcache.client.base import PooledClient
import json


lock = Lock()

# Datastructure is in the form of:
#  devicename/measurements: for each measurement type: value.
# New value is a flag to know if value has been updated since last SQL-query. -> Each :00, :30
def main():
    tmpdata = {
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
    new_values = {location: {key: False for key in subloc} for location, subloc in tmpdata.items()}

    memcache = PooledClient("memcached:11211", serde=JSerde(), max_pool_size=3)

    # Set initial values.
    memcache.set("weather_data_home", tmpdata["home"])
    memcache.set("weather_data_remote_sh", tmpdata["remote_sh"])

    Thread(
        target=mqtt_agent,
        args=(
            tmpdata["home"],
            new_values["home"],
            memcache,
        ),
        daemon=True,
    ).start()
    Thread(
        target=remote_fetcher,
        args=(
            tmpdata["remote_sh"],
            new_values["remote_sh"],
            memcache,
            "remote_sh",
        ),
        daemon=True,
    ).start()
    schedule_setup(tmpdata, new_values)

    # Poll tmpdata until all Nones are gone.
    while 1:
        time.sleep(1)
        for value_list in tmpdata["home"].values():
            if -99 in value_list.values():
                break
        else:
            break

    while 1:
        schedule.run_pending()
        time.sleep(10)


def remote_fetcher(remotedata, rem_new_values, memcache, rem_key):
    from bmemcached import Client
    import configparser
    import pathlib

    # This could be a great use of asyncio... Maybe when I understand it for a later project.
    cfg = configparser.ConfigParser()
    cfg.read(pathlib.Path(__file__).parent.absolute() / "config.ini")
    memcachier1 = Client((cfg["DATA"]["server"],), cfg["DATA"]["user"], cfg["DATA"]["pass"])
    memcachier2 = Client((cfg["DATA2"]["server"],), cfg["DATA2"]["user"], cfg["DATA2"]["pass"])

    count_error = 0
    last_update_remote = {key: datetime.now() for key in remotedata}
    last_update_memcachier = datetime.now()  # Just as init
    while 1:
        time.sleep(15)
        try:
            # Get the latest value from two sources.. woohoo
            # Test every possiblity...
            value1 = memcachier1.get(rem_key)
            value2 = memcachier2.get(rem_key)
            if value1 is None:
                if value2 is None:
                    count_error = 1 if count_error >= 20 else count_error + 1
                    continue
                else:
                    value = json.loads(value2)
            else:
                if value2 is None:
                    value = json.loads(value1)
                else:
                    value1 = json.loads(value1)
                    value2 = json.loads(value2)
                    try:
                        t1 = datetime.fromisoformat(value1[2])
                        try:
                            t2 = datetime.fromisoformat(value[2])
                            value = value1 if t1 >= t2 else value2
                        except:
                            value = value1
                    except:
                        value = value2

            # At this point value or exception thrown.
            memcache.set("remote_sh_rawdata", value)
            this_time = datetime.fromisoformat(value.pop(-1))
            if this_time >= last_update_memcachier:
                last_update_memcachier = this_time
                count_error = 0

                new_tmpdata, data_updatetime = value
                for measr, valuedict in new_tmpdata.items():
                    tmpdict = {}
                    # Test if new updatetime is newer than last. Otherwise continue.
                    updatetime = datetime.fromisoformat(data_updatetime[measr])
                    if updatetime >= last_update_remote[measr]:
                        for key, val in valuedict.items():
                            if key in remotedata[measr] and _test_value(key, int(val * 100)):
                                tmpdict[key] = val
                            else:
                                break
                        else:
                            memcache.set(f"weather_data_{rem_key}", remotedata)
                            last_update_remote[measr] = updatetime
                            with lock:
                                remotedata[measr].update(tmpdict)
                                rem_new_values[measr] = True
        except:
            count_error += 1
            if count_error >= 20:
                # Set to invalid values after n attempts. Reset counter.
                count_error = 1
                with lock:
                    for measurer, valuedict in remotedata.items():
                        for key, _ in valuedict.items():
                            remotedata[measurer][key] = -99
                            rem_new_values[measurer] = False


# mqtt function does all the heavy lifting sorting out bad data.
def schedule_setup(tmp_data: dict, new_values: dict):
    def querydb():
        # Check if there exist any values that should be queried. To reduce as much time with lock.
        queryloc = []
        for location, locdict in new_values.items():
            if any(locdict.values()):
                queryloc.append(location)

        if not queryloc:
            return

        # Copy tmpdata, slight mistiming doesn't matter but if one thread changes to -99 while reading...
        # Set values to false to reduce time with lock. In case I/O gets slowed down...
        with lock:
            tmpdata = tmp_data.copy()
            new_val = new_values.copy()
            for loc in queryloc:
                for k in new_values[loc]:
                    new_values[loc][k] = False
        time_now = datetime.now().isoformat("T", "minutes")
        cursor = db.cursor()
        cursor.execute(f"INSERT INTO Timestamp VALUES ('{time_now}')")
        for location in queryloc:
            for measurer, valuedict in tmpdata[location].items():
                if not new_val[location][measurer]:
                    continue
                mkey = measurer.split("/")[0]
                for table, val in valuedict.items():
                    cursor.execute(f"INSERT INTO {table} VALUES ('{mkey}', '{time_now}', {val})")
        db.commit()
        cursor.close()

    db = sqlite3.connect("/db/main_db.db")
    schedule.every().hour.at(":30").do(querydb)
    schedule.every().hour.at(":00").do(querydb)

def mqtt_agent(h_tmpdata: dict, h_new_values: dict, memcache, status_path="balcony/relay/status"):
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
    client = mqtt.Client("br_logger")
    client.on_connect = on_connect
    client.on_message = on_message
    while True:
        try:
            if client.connect("www.home", 1883, 60) == 0:
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


# setup memcache
class JSerde(object):
    def serialize(self, key, value):
        return json.dumps(value), 2


if __name__ == "__main__":
    main()

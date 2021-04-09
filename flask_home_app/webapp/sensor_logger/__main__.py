from ast import literal_eval
import paho.mqtt.client as mqtt
from datetime import datetime
import sqlite3
from threading import Thread
import schedule
import time
from pymemcache.client.base import PooledClient
import json

# Setup and run. Scheduler queries database every full or half hour. Mqtt queries tempdata to memory.
def main():
    tmpdata = {
        "bikeroom/temp": {"Temperature": -99},
        "balcony/temphumid": {"Temperature": -99, "Humidity": -99},
        "kitchen/temphumidpress": {"Temperature": -99, "Humidity": -99, "Airpressure": -99},
    }
    remotedata = {"remote_sh": None}

    memcache = PooledClient("memcached:11211", serde=JSerde(), max_pool_size=2)

    Thread(target=mqtt_agent, args=(tmpdata, memcache), daemon=True).start()
    Thread(target=remote_fetcher, args=(remotedata, memcache), daemon=True).start()
    schedule_setup(tmpdata, remotedata)

    # Poll tmpdata until all Nones are gone.
    while 1:
        time.sleep(1)
        for value_list in tmpdata.values():
            if -99 in value_list.values():
                break
        else:
            break

    while 1:
        schedule.run_pending()
        time.sleep(10)


def remote_fetcher(remotedata, memcache):
    from bmemcached import Client
    import configparser
    import pathlib

    # This could be a great use of asyncio... Maybe when I understand it for a later project.
    cfg = configparser.ConfigParser()
    cfg.read(pathlib.Path(__file__).parent.absolute() / "config.ini")
    memcachier1 = Client((cfg["DATA"]["server"],), cfg["DATA"]["user"], cfg["DATA"]["pass"])
    memcachier2 = Client((cfg["DATA2"]["server"],), cfg["DATA2"]["user"], cfg["DATA2"]["pass"])

    last_time = None
    count_error = 0
    while 1:
        time.sleep(10)
        try:
            value = memcachier1.get("remote_sh")
            if not value:
                value = memcachier2.get("remote_sh")
            if value:
                jsondata = json.loads(value)
                if not (this_time := jsondata.pop("Time")) == last_time:
                    last_time = this_time
                    count_error = 0

                    newdata = {}
                    for i in ("Temperature", "Temp_hydro", "Airpressure", "Humidity"):
                        if i not in jsondata:
                            break
                        value = jsondata.pop(i)
                        if not _test_value(i, value):
                            break
                        newdata[i] = value / 100
                    else:
                        remotedata["remote_sh"] = newdata
                        memcache.set("remote_sh", newdata | {"Time": this_time})
                        continue
        except:
            pass
        # If nothing continues in try statement, then there is an error.
        count_error += 1
        if count_error >= 20:
            # Set to invalid values after n attempts. Reset counter.
            count_error = 0
            remotedata["remote_sh"] = None


# mqtt function does all the heavy lifting sorting out bad data.
def schedule_setup(tmpdata: dict, remotedata: dict):
    def insert_db(cursor, datadict, time_now):
        for location, data in datadict.items():
            if not data:
                continue
            measurer = location.split("/")[0]
            for table, value in data.items():
                cursor.execute(f"INSERT INTO {table} VALUES ('{measurer}', '{time_now}', {value})")

    def querydb():
        time_now = datetime.now().isoformat("T", "minutes")
        cursor = db.cursor()
        cursor.execute(f"INSERT INTO Timestamp VALUES ('{time_now}')")
        insert_db(cursor, tmpdata, time_now)
        insert_db(cursor, remotedata, time_now)
        db.commit()
        cursor.close()

    db = sqlite3.connect("/db/database.db")
    schedule.every().hour.at(":30").do(querydb)
    schedule.every().hour.at(":00").do(querydb)


def mqtt_agent(tmpdata: dict, memcache, status_path="balcony/relay/status"):
    def on_connect(client, *_):
        for topic in list(tmpdata.keys()) + [status_path]:
            client.subscribe("home/" + topic)

    def on_message(client, userdata, msg):
        topic = msg.topic.replace("home/", "")
        if topic not in tmpdata:
            return
        # Might redo the function to be more readable. Might taken optimization too far... :)
        try:
            listlike = literal_eval(msg.payload.decode("utf-8"))
            if isinstance(listlike, dict):
                listlike = tuple(listlike.values())
            elif not (isinstance(listlike, tuple) or isinstance(listlike, list)):
                listlike = (listlike,)
        except:
            return
        if status_path in topic:
            if not set(listlike).difference(set((0, 1))) and len(listlike) == 4:
                memcache.set("relay_status", listlike)
            return
        if len(listlike) != len(tmpdata[topic]):
            return
        for key, value in zip(tmpdata[topic].keys(), listlike):
            if not _test_value(key, value):
                continue
            tmpdata[topic][key] = value / 100
        memcache.set("weather_data_home", tmpdata)

    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect("www.home", 1883, 60)
    client.loop_forever()

def _test_value(key, value) -> bool:
    if isinstance(value, int):
        if key in ("Temperature", "Temp_hydro"):
            return -5000 <= value <= 5000
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

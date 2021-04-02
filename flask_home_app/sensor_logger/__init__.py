from ast import literal_eval
import paho.mqtt.client as mqtt
from datetime import datetime
import sqlite3
from threading import Thread
import schedule
import time
from pathlib import Path

# Setup and run.
def main():
    # Tempdata
    tmpdata = {
        "bikeroom/temp": {"Temperature": None},
        "balcony/temphumid": {"Temperature": None, "Humidity": None},
        "kitchen/temphumidpress": {"Temperature": None, "Humidity": None, "Airpressure": None},
    }

    Thread(target=mqtt_agent, args=(tmpdata,), daemon=True).start()

    schedule_setup(Path.cwd().parent / "webapp" / "backend" / "database.db", tmpdata)

    while True:
        schedule.run_pending()
        time.sleep(5)


# "dumb" method, this just adds values if each set of values doesn't contain None.
# mqtt function does all the heavy lifting sorting out bad data.
def schedule_setup(db, tmpdata):
    def querydb():
        list_to_query = []
        for location, value_list in tmpdata.items():
            if None in value_list.values():
                continue
            list_to_query.append(location)

        if not list_to_query:
            return

        time_now = datetime.now().isoformat("T", "minutes")
        con = sqlite3.connect(db)
        cur = con.cursor()
        cur.execute(f"INSERT INTO Timestamp VALUES ({time_now})")
        for location in list_to_query:
            measurer = location.split("/")[0]
            for table, value in tmpdata[location].items():
                cur.execute(f"INSERT INTO {table} VALUES ({measurer}, {time_now}, {value})")
        con.commit()
        con.close()

    schedule.every().hour.at(":30").do(querydb)
    schedule.every().hour.at(":00").do(querydb)


# This agent only needs threading. Multiprocessing is nicer but I don't expect too much concurrency
# on this webapp. Small microseconds delay are no problem at home.
def mqtt_agent(tmpdata):
    def on_connect(client, *_):
        for topic in tmpdata.keys():
            client.subscribe("home/" + topic)

    def on_message(client, userdata, msg):
        topic = msg.topic.replace("home/", "")
        if topic not in tmpdata.keys():
            return
        # Test if data is a listlike or a value.
        try:
            listlike = literal_eval(msg.payload.decode("utf-8"))
            if isinstance(listlike, dict):
                listlike = tuple(listlike.values())
            elif not (isinstance(listlike, tuple) or isinstance(listlike, list)):
                listlike = (listlike,)
        except:
            return
        if len(listlike) != len(tmpdata[topic]):
            return
        for key, value in zip(tmpdata[topic].keys(), listlike):
            if not isinstance(value, int):
                continue
            if key == "Temperature" and not -2500 <= value <= 5000:
                continue
            elif key == "Humidity" and not 0 <= value <= 10000:
                continue
            elif key == "Airpressure" and not 90000 <= value <= 115000:
                continue
            elif key not in ("Temperature", "Humidity", "Airpressure"):
                continue
            tmpdata[topic][key] = value / 100

    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect("www.home", 1883, 60)
    client.loop_forever(timeout=1)


if __name__ == "__main__":
    main()

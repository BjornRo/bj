from datetime import datetime
import json
import glob
import configparser
import pathlib
from bmemcached import Client as mClient
from time import sleep

from asyncio_mqtt import Client
import aiosqlite
import asyncio
import aiofiles

# Defined read only global variables
# Find the device file to read from.
device_file = glob.glob("/sys/bus/w1/devices/28*")[0] + "/w1_slave"
# To stop subscribing to non-existing devices.
sub_denylist = ("pizw/temp",)


def main():
    while 1:
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

        cfg = configparser.ConfigParser()
        cfg.read(pathlib.Path(__file__).parent.absolute() / "config.ini")

        db = aiosqlite.connect("/db/remote_sh.db")

        #asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(mqtt_agent(tmpdata, new_values, last_update))
            loop.create_task(read_temp(tmpdata, new_values, "pizw/temp", last_update))
            loop.create_task(querydb(db, tmpdata, new_values))
            loop.create_task(memcache_as(cfg, tmpdata, last_update))
            loop.run_forever()
        except:
            pass
        finally:
            try:
                try:
                    loop.run_until_complete(db.close())
                except:
                    pass
                loop.run_until_complete(loop.shutdown_asyncgens())
                loop.run_until_complete(loop.shutdown_default_executor())
            finally:
                loop.close()
                sleep(20)
                asyncio.set_event_loop(asyncio.new_event_loop())


async def memcache_as(cfg, tmpdata, last_update):
    loop = asyncio.get_event_loop()
    m1 = mClient((cfg["DATA"]["server"],), cfg["DATA"]["user"], cfg["DATA"]["pass"])
    m2 = mClient((cfg["DATA2"]["server"],), cfg["DATA2"]["user"], cfg["DATA2"]["pass"])
    def memcache():
        data = json.dumps((tmpdata, last_update, datetime.now().isoformat()))
        m1.set("remote_sh", data)
        m2.set("remote_sh", data)
    while 1:
        try:
            await asyncio.sleep(10)
            await loop.run_in_executor(None, memcache)
        except:
            pass


async def mqtt_agent(tmpdata, new_values, last_update):
    while 1:
        try:
            async with Client("192.168.1.200") as client:
                for topic in tmpdata:
                    if topic not in sub_denylist:
                        await client.subscribe("landet/" + topic)
                async with client.unfiltered_messages() as messages:
                    async for message in messages:
                        on_message(tmpdata, new_values, last_update, message)
        except:
            pass
        await asyncio.sleep(5)


# Since mqtt_agent is async, thus this is sync, no race conditions.
#  -> Either MQTT or SQL, but not both.
def on_message(tmpdata, new_values, last_update, message):
    # Get values into a __iter__ form. msg is in bytes
    try:
        msg = message.payload
        # Check if string has ( and ) or [ and ]
        if (msg[0] == 40 and msg[-1] == 41) or (msg[0] == 91 and msg[-1] == 93):
            listlike = tuple(map(int, msg[1:-1].split(b",")))
        elif msg.isdigit():
            listlike = (int(msg),)
        else: # dict
            listlike = json.loads(msg)
        # Handle the topic depending on what it is about.
        topic = message.topic[7:]
        if len(listlike) != len(tmpdata[topic]):
            return

        for key, value in zip(tmpdata[topic], listlike):
            # If a device sends bad data -> break and discard, else update
            if not _test_value(key, value):
                break
            tmpdata[topic][key] = value / 100
        else:
            new_values[topic] = True
            last_update[topic] = datetime.now().isoformat()
    except:  # Unsupported datastructures or invalid values
        return


async def querydb(db: aiosqlite.Connection, tmpdata: dict, new_values: dict):
    await db
    while not all(new_values.values()):
        await asyncio.sleep(5)
    while 1:
        dt = datetime.now()
        await asyncio.sleep(((1800 - dt.minute * 60 - dt.second) % 1800) + 5)
        try:
            if any(new_values.values()):
                # Get a snapshot of the data
                tmpdata_copy, new_values_copy = tmpdata.copy(), new_values.copy()
                # Reset new values while in control.
                for k in new_values:
                    new_values[k] = False
                dt = datetime.now()
                dt = dt.replace(minute=30 * (dt.minute // 30)).isoformat("T", "minutes")

                # Async query
                cursor = await db.cursor()
                await cursor.execute(f"INSERT INTO Timestamp VALUES ('{dt}')")
                for location, data in tmpdata_copy.items():
                    if not new_values_copy[location]:
                        continue
                    mkey = location.split("/")[0]
                    for tb, val in data.items():
                        await cursor.execute(f"INSERT INTO {tb} VALUES ('{mkey}', '{dt}', {val})")
                await db.commit()
                await cursor.close()
        except:
            pass
        await asyncio.sleep(600)


async def read_temp(tmpdata: dict, new_values: dict, measurer: str, last_update: dict):
    while 1:
        found = False
        try:
            async with aiofiles.open(device_file, "r") as f:
                async for line in f:
                    line = line.strip()
                    if not found and line[-3:] == "YES":
                        found = True
                        continue
                    elif found:
                        equals_pos = line.find("t=")
                        if equals_pos != -1 and (tmp_val := line[equals_pos + 2 :]).isdigit():
                            conv_val = round(int(tmp_val) / 1000, 1)
                            if _test_value("Temperature", conv_val * 100):
                                tmpdata[measurer]["Temperature"] = conv_val
                                new_values[measurer] = True
                                last_update[measurer] = datetime.now().isoformat()
                    break
        except:
            pass
        await asyncio.sleep(4)


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

from datetime import datetime, timedelta
import json
import glob
import configparser
import pathlib
from aiosqlite.core import connect
from bmemcached import Client as mClient
from time import sleep

from asyncio_mqtt import Client
import aiosqlite
import asyncio
import aiofiles

cfg = configparser.ConfigParser()
cfg.read(pathlib.Path(__file__).parent.absolute() / "config.ini")

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



        # asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(mqtt_agent(tmpdata, new_values, last_update))
            loop.create_task(read_temp(tmpdata, new_values, "pizw/temp", last_update))
            loop.create_task(querydb(tmpdata, new_values))
            loop.create_task(memcache_as(tmpdata, last_update))
            loop.run_forever()
        finally:
            try:
                loop.run_until_complete(loop.shutdown_asyncgens())
                loop.run_until_complete(loop.shutdown_default_executor())
            finally:
                loop.close()
                sleep(20)
                asyncio.set_event_loop(asyncio.new_event_loop())


async def memcache_as(tmpdata, last_update):
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
        else:  # dict
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


async def querydb(tmpdata: dict, new_values: dict):
    while not any(new_values.values()):
        await asyncio.sleep(5)
    while 1:
        # Old algo ((1800 - dt.minute * 60 - 1) % 1800) - dt.second + 1

        # Get time to sleep. Expensive algorithm, but queries are few.
        dt = datetime.now()
        nt = dt.replace(second=0, microsecond=0) + timedelta(minutes=(30 - dt.minute - 1) % 30 + 1)
        await asyncio.sleep((nt - dt).total_seconds())
        # If timer gone too fast and there are seconds left, wait the remaining time, else continue.
        if (remain := (nt - datetime.now()).total_seconds()) > 0:
            await asyncio.sleep(remain)
        if not any(new_values.values()):
            continue
        try:
            dt = nt.isoformat("T", "minutes")
            # Copy values because we don't know how long time the queries will take.
            tmp_dict = {}
            for key, value in new_values.items():
                if value:
                    new_values[key] = False
                    tmp_dict[key] = tmpdata[key].copy()
            async with aiosqlite.connect("/db/remote_sh.db") as db:
                await db.execute(f"INSERT INTO Timestamp VALUES ('{dt}')")
                for measurer, data in tmp_dict.items():
                    mkey = measurer.split("/")[0]
                    for tb, val in data.items():
                        await db.execute(f"INSERT INTO {tb} VALUES ('{mkey}', '{dt}', {val})")
                await db.commit()
        except:
            pass


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

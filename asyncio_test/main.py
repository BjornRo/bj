import asyncio
import aiosqlite
from datetime import datetime
import aiofiles
import json
import glob
import aiomcache
from asyncio_mqtt import Client, MqttError

"""
    This won't be 100% accurate due to pi zero vs desktop... Just to implement the idea
    and proof of concept. Reducing overhead of threading and locks is the goal.
    Also understanding asyncio. Knowledge != understanding. Async as a concept in small
    scale is easy, for a module.. nope.

    # Some speed testing -> Copy dict and let async continue or locking the resource
    lock = Lock()
    b = False
    if b:
        timeit.timeit(lambda: t(), number=1000000)

    def t():
        with lock:
            tv = tmpdata.copy()
    """

directory = "C:\\Users\\bjorn\\Documents\\git_repos\\doodle_repo\\asyncio_test\\"


async def main():
    tmpdata = {
        "pizw/temp": {
            "Temperature": -99,
        },
        "kitchen/temphumidpress": {
            "Temperature": -99,
            "Humidity": -99,
            "Airpressure": -99,
        },
    }
    new_values = {key: False for key in tmpdata}
    last_update = {key: None for key in tmpdata}
    last_schedule = None

    # Only one entity accessess the database. No need to close.
    db = await aiosqlite.connect(directory + "\\db.db")

    while 1:
        read_temp(tmpdata, new_values, "pizw/temp", last_update)

        if (minute := scheduler((0, 30), last_schedule)) is not None:
            last_schedule = minute
            await querydb(db, tmpdata, new_values, minute)

async def mqtt_agent():
    while 1:
        try:
            async with Client("192.168.1.200") as client:
                async with client.unfiltered_messages() as messages:
                    await client.subscribe("home/#")
                    async for message in messages:
                        print(message.payload.decode())
        except KeyboardInterrupt:
            import sys
            sys.exit(1)
        await asyncio.sleep(5)

asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(mqtt_agent())


async def querydb(db: aiosqlite.Connection, tmpdata: dict, new_values: dict, minutes_xs):
    while 1:
        dt = datetime.now()
        await asyncio.sleep(((30 - dt.minute) % 30) * 60 - dt.second + 5)
        if any(new_values.values()):
            # Get a snapshot of the data
            data, nv = tmpdata.copy(), new_values.copy()
            # Reset new values while in control.
            for k in new_values:
                new_values[k] = False
            dt = datetime.now()
            dt = dt.replace(minute=30 * (dt.minute // 30)).isoformat("T", "minutes")

            # Async query
            cursor = await db.cursor()
            await cursor.execute(f"INSERT INTO Timestamp VALUES ('{dt}')")
            for loc, data in data.items():
                if not nv[loc]:
                    continue
                mkey = loc.split("/")[0]
                for tb, val in data.items():
                    await cursor.execute(f"INSERT INTO {tb} VALUES ('{mkey}', '{dt}', {val})")
            await db.commit()
            await cursor.close()


async def read_temp(tmpdata: dict, new_values: dict, measurer: str, last_update: dict):
    while 1:
        found = False
        try:
            async with aiofiles.open(directory + "mocktemp", "r") as f:
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
        await asyncio.sleep(5)

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


asyncio.run(main())


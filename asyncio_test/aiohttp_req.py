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
last_update = {key: None for key in tmpdata}  # For main node to know when sample was taken.

import asyncio
from aiohttp import web
import json

async def handler(request):
    return web.json_response([1,2,3,4])


async def main():
    server = web.Server(handler)
    runner = web.ServerRunner(server)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 80)
    await site.start()

    # pause here for very long time by serving HTTP requests and
    # waiting for keyboard interruption


loop = asyncio.get_event_loop()

async def side():
    await asyncio.sleep(5)

try:
    loop.create_task(main())
    #loop.create_task(side())
    loop.run_forever()
except KeyboardInterrupt:
    pass
loop.close()

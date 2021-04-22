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

routes = web.RouteTableDef()
@routes.get("/status")
async def handler(request):
    a = (tmpdata, last_update)
    tmpdata['pizw/temp']["Temperature"] += 1
    return web.json_response(a)


async def main():
    server = web.Server(handler)
    runner = web.ServerRunner(server)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 42660)
    await site.start()

    print("======= Serving on http://127.0.0.1:8080/ ======")

    # pause here for very long time by serving HTTP requests and
    # waiting for keyboard interruption


loop = asyncio.get_event_loop()

async def side():
    await asyncio.sleep(5)

try:

    app = web.Application()
    app.add_routes(routes)
    loop.create_task(main())
    #loop.create_task(side())
    loop.run_forever()
    web.run_app(app)
except KeyboardInterrupt:
    pass
loop.close()

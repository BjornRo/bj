import random
import asyncio
from time import sleep
import sys

async def runner():
    global loop
    for _ in range(5):
        await blocker()
        print("Running!")
    print("Done running!")
    asyncio.stop()

async def blocker():
    print("Doing heavy async IO task!")
    await asyncio.sleep(1)

async def seconder():
    while 1:
        print("Secondary running task!")
        rnd = random.randint(1,10)
        await asyncio.sleep(rnd/10)


# async def main():
#     asyncio.create_task(runner())
#     await asyncio.create_task(seconder())

# loop = asyncio.new_event_loop()
# loop.create_task(runner())
# loop.create_task(seconder())
# loop.run_forever()
# loop.close()

async def recursive(n):
    if n <= 0:
        pass
    else:
        if n % 2 == 0:
            print("Hello")
        await asyncio.sleep(1)
        await asyncio.create_task(recursive(n-1))


async def main():
    await recursive(5)

sys.setrecursionlimit(100)

try:
    loop = asyncio.get_event_loop()
    loop.run_until_complete(recursive(10))
finally:
    loop.close()
    asyncio.set_event_loop(asyncio.new_event_loop())
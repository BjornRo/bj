import random
import asyncio
from time import sleep
import sys
from datetime import datetime

async def seconder():
    pass

async def main():
    pass


try:
    loop = asyncio.get_event_loop()
    print(loop.time())
finally:
    loop.close()
    asyncio.set_event_loop(asyncio.new_event_loop())
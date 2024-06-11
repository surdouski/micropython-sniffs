import asyncio
from usniffs.router import Router


class Sniffs:
    """A dynamic wrapper for the mqtt_as client (mqtt_as wrote by Peter Hinch)."""

    def __init__(self, *args, **kwargs):
        self.client = None
        self.router = Router()

    async def bind(self, client):
        self.client = client

        asyncio.create_task(self._up())
        asyncio.create_task(self._messages())
        asyncio.create_task(self._down())

        await asyncio.sleep(10)  # maybe this is not a great strategy; revisit this

    def route(self, topic_pattern: str):
        """inspect_args is a workaround for micropython lacking the ability to inspect function arguments."""

        def decorator(func):
            self.router.add_route(topic_pattern, func)
            return func  # Return the original function instead of a wrapper

        return decorator

    async def _up(self):
        while True:
            await self.client.up.wait()
            self.client.up.clear()
            print("We are connected to broker.")
            paths = self.router.get_topic_paths()
            for path in paths:
                print(f"Subscribing to {path}")
                await self.client.subscribe(path)

    async def _down(self):
        while True:
            await self.client.down.wait()  # Pause until outage
            self.client.down.clear()
            print("WiFi or broker is down.")

    async def _messages(self):
        async for topic, msg, retained in self.client.queue:
            await self.router.route(topic.decode(), msg.decode())

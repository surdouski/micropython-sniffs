import asyncio

from usniffs.returns import AwaitableReturns
from usniffs.router import Router


class Sniffs:
    """A dynamic wrapper for the mqtt_as client (mqtt_as wrote by Peter Hinch)."""

    def __init__(self, on_connect=None, on_disconnect=None, *args, **kwargs):
        self.client = None
        self._awaitable_returns = AwaitableReturns()
        self.router = Router(self._awaitable_returns)
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect

    async def bind(self, client):
        self.client = client

        asyncio.create_task(self._up())
        asyncio.create_task(self._messages())
        asyncio.create_task(self._down())

        await asyncio.sleep(0)

    def route(self, topic_route: str):
        """A decorator for adding route registration."""

        def decorator(func):
            route = self._awaitable_returns.add_awaitable_route(topic_route)
            self.router.register(topic_route, func)
            return route

        return decorator

    async def _up(self):
        while True:
            await self.client.up.wait()
            self.client.up.clear()

            print("We are connected to broker.")
            paths = self.router.get_topic_paths()
            for path in paths:
                await self.client.subscribe(path)

            if self.on_connect:
                await self.on_connect()

    async def _down(self):
        while True:
            await self.client.down.wait()  # Pause until outage
            self.client.down.clear()
            print("WiFi or broker is down.")

            if self.on_disconnect:
                await self.on_disconnect()

    async def _messages(self):
        async for topic, msg, retained in self.client.queue:
            await self.router.route(topic.decode(), msg.decode())

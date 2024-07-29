import asyncio


class _AwaitableRoute:
    def __init__(self, route):
        self._route = route
        self.result = None
        self.ready = asyncio.Event()

    def trigger(self, result):
        self.result = result
        self.ready.set()

    async def fetch_next_result(self):
        await self.ready.wait()
        self.ready.clear()
        return self.result  # updated when triggered

    def __await__(self):
        res = yield from self.fetch_next_result()
        return res

    __iter__ = __await__


class AwaitableReturns:
    def __init__(self):
        self._awaitable_routes = {}

    def add_awaitable_route(self, route: str) -> _AwaitableRoute:
        awaitable_route = _AwaitableRoute(route)
        self._awaitable_routes[route] = awaitable_route
        return awaitable_route

    def trigger_awaitable_route(self, route: str, result) -> None:
        if self._awaitable_routes.get(route):
            self._awaitable_routes[route].trigger(result)

"""
This included in top level directory to make testing simpler for now -- will take another
look at the repo layout in the future.
"""

import asyncio
import unittest
from usniffs import Router, Sniffs, AwaitableReturns

_updated = False
_update_dict = {}


async def _handler():
    global _updated
    _updated = True


async def _handler__any_variable__topic__message(any_variable, topic, message):
    global _updated
    _updated = True
    _update_dict["any_variable"] = any_variable
    _update_dict["topic"] = topic
    _update_dict["message"] = message


async def _handler__topic__message__room__sensor(topic, message, room, sensor):
    global _updated
    _updated = True
    _update_dict["topic"] = topic
    _update_dict["message"] = message
    _update_dict["room"] = room
    _update_dict["sensor"] = sensor


class TestRouter(unittest.TestCase):
    def setUp(self):
        global _updated
        global _update_dict
        _updated = False
        _update_dict = {}
        self.router = Router(AwaitableReturns())

    def test_route_no_replacement(self):
        async def run_test():
            self.router.register("home/+/temperature", _handler)
            await self.router.route("home/truly_anything/temperature", "")
            self.assertTrue(_updated)

        asyncio.run(run_test())

    def test_route_one_replacement(self):
        async def run_test():
            self.router.register("home/<some_replacement>/temperature", _handler)
            await self.router.route("home/truly_anything/temperature", "")
            self.assertTrue(_updated)

        asyncio.run(run_test())

    def test_route_two_replacements(self):
        async def run_test():
            self.router.register("home/<replace_1>/<replace_2>", _handler)
            await self.router.route("home/truly_anything/mostly", "")
            self.assertTrue(_updated)

        asyncio.run(run_test())

    def test_route_named_replacement(self):
        async def run_test():
            self.router.register(
                "home/<room>:{living_room,kitchen}/temperature", _handler
            )
            await self.router.route("home/kitchen/temperature", "")
            self.assertTrue(_updated)

        asyncio.run(run_test())

    def test_route_two_named_replacements(self):
        async def run_test():
            self.router.register(
                "home/<room>:{living_room,kitchen}/<sensor>:{sensor1,sensor2}", _handler
            )
            await self.router.route("home/living_room/sensor2", "")
            self.assertTrue(_updated)

        asyncio.run(run_test())

    def test_route(self):
        async def run_test():
            self.router.register(
                "home/<any_variable>/temperature",
                _handler__any_variable__topic__message,
            )
            await self.router.route("home/kitchen/temperature", "20")
            self.assertTrue(_updated)
            self.assertEqual(_update_dict["any_variable"], "kitchen")
            self.assertEqual(_update_dict["topic"], "home/kitchen/temperature")
            self.assertEqual(_update_dict["message"], "20")

        asyncio.run(run_test())

    def test_route_multiple_groups(self):
        async def run_test():
            self.router.register(
                "home/<room>:{kitchen,living_room}/<sensor>:{sensor2,temperature}",
                _handler__topic__message__room__sensor,
            )
            await self.router.route("home/kitchen/temperature", "20")
            self.assertTrue(_updated)
            self.assertEqual(_update_dict["topic"], "home/kitchen/temperature")
            self.assertEqual(_update_dict["message"], "20")
            self.assertEqual(_update_dict["room"], "kitchen")
            self.assertEqual(_update_dict["sensor"], "temperature")

        asyncio.run(run_test())


sniffs = Sniffs()
_topic = ""
_message = ""
_sniffs_route_updated = False


@sniffs.route("home/<one>/<two>")
async def _routing_function_one(one, two):
    return (one, two)


@sniffs.route("home/<testing>:{foo,bar}/temperature")
async def _routing_function_two(testing, topic, message):
    global _topic
    global _message
    global _sniffs_route_updated
    _topic = topic
    _message = message
    _sniffs_route_updated = True
    return testing


@sniffs.route("foo/+/+")
async def _routing_wildcard():
    global _sniffs_route_updated
    _sniffs_route_updated = True


@sniffs.route("awaitable/function")
async def _awaitable_function():
    return "awaitable function return value"


class TestSniffs(unittest.TestCase):
    def setUp(self):
        global _topic
        global _message
        global _sniffs_route_updated
        _topic = ""
        _message = ""
        _sniffs_route_updated = False

    def test_route_decorator(self):
        async def run_test():
            output = await sniffs.router.route("home/anything/really", "some message")
            self.assertIn(("anything", "really"), output)
            self.assertFalse(_sniffs_route_updated)

        asyncio.run(run_test())

    def test_real_route_decorator(self):
        async def run_test():
            output = await sniffs.router.route("home/foo/temperature", "a message")
            self.assertIn("foo", output)
            self.assertTrue(_sniffs_route_updated)

        asyncio.run(run_test())

    def test_multiple_routes_applicable(self):
        async def run_test():
            output = await sniffs.router.route("home/bar/temperature", "new message")
            self.assertEqual(
                output, (("bar", "temperature"), "bar")
            )  # both routes are called
            self.assertEqual(_message, "new message")
            self.assertEqual(_topic, "home/bar/temperature")
            self.assertTrue(_sniffs_route_updated)

        asyncio.run(run_test())

    def test_wildcard(self):
        async def run_test():
            await sniffs.router.route("foo/ta/da", "doesn't matter")
            self.assertTrue(_sniffs_route_updated)

        asyncio.run(run_test())

    def test_awaitable_function(self):
        async def run_test():
            asyncio.create_task(
                sniffs.router.route("home/bar/temperature", "another message")
            )
            the_return = await _awaitable_function
            self.assertEqual(the_return, "awaitable function return value")

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()

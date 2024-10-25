"""
This included in top level directory to make testing simpler for now -- will take another
look at the repo layout in the future.
"""

import asyncio
import unittest
from usniffs import Router, Sniffs, AwaitableReturns
from usniffs.utils import arg_names

_updated = False
_updated2 = False
_update_dict = {}


def sync_foo(a, b, c, d, e, f):
    ...

async def async_foo(a, b, c, d, e, f):
    ...

class BarClass:
    def bound_foo(self, a, b, c, d, e, f):
        ...

bound_foo = BarClass().bound_foo


async def _handler():
    global _updated
    _updated = True


async def _handler2():
    global _updated2
    _updated2 = True


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
        global _updated2
        global _update_dict
        _updated = False
        _updated2 = False
        _update_dict = {}
        self.router = Router(AwaitableReturns())

    def test_route_no_replacement(self):
        self.router.register("home/+/temperature", _handler)
        paths = self.router.get_topic_paths()
        expected_paths = [
            "home/+/temperature",
        ]
        assert len(paths) == len(expected_paths)
        for path in paths:
            assert path in expected_paths, f"{path} not in {expected_paths}"

    def test_route_one_replacement(self):
        self.router.register("home/<some_replacement>/temperature", _handler)
        paths = self.router.get_topic_paths()
        expected_paths = [
            "home/+/temperature",
        ]
        assert len(paths) == len(expected_paths)
        for path in paths:
            assert path in expected_paths, f"{path} not in {expected_paths}"

    def test_route_two_replacements(self):
        self.router.register("home/<replace_1>/<replace_2>", _handler)
        paths = self.router.get_topic_paths()
        expected_paths = [
            "home/+/+",
        ]
        assert len(paths) == len(expected_paths)
        for path in paths:
            assert path in expected_paths, f"{path} not in {expected_paths}"


    def test_route_named_replacement(self):
        self.router.register(
            "home/<room>:{living_room,kitchen}/temperature", _handler
        )
        paths = self.router.get_topic_paths()
        expected_paths = [
            "home/living_room/temperature",
            "home/kitchen/temperature",
        ]
        assert len(paths) == len(expected_paths)
        for path in paths:
            assert path in expected_paths, f"{path} not in {expected_paths}"

    def test_route_two_named_replacements(self):
        self.router.register(
            "home/<room>:{living_room,kitchen}/<sensor>:{sensor1,sensor2}", _handler
        )
        paths = self.router.get_topic_paths()
        expected_paths = [
            "home/living_room/sensor1",
            "home/living_room/sensor2",
            "home/kitchen/sensor1",
            "home/kitchen/sensor2",
        ]
        assert len(paths) == len(expected_paths)
        for path in paths:
            assert path in expected_paths, f"{path} not in {expected_paths}"

    def test_route_substring_replacement_part_of_other_topic(self):
        self.router.register(
            "devices/<device>:{device1,device2}/anything", _handler
        )
        paths = self.router.get_topic_paths()
        expected_paths = [
            "devices/device1/anything",
            "devices/device2/anything"
        ]
        assert len(paths) == len(expected_paths)
        for path in paths:
            assert path in expected_paths, f"{path} not in {expected_paths}"

    def test_route_does_not_match_partial_route(self):
        async def run_test():
            self.router.register("test/first", _handler)
            self.router.register("test/first/second", _handler2)
            await self.router.route("test/first/second", "")
            self.assertFalse(_updated)
            self.assertTrue(_updated2)

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
    on_connect_called = False
    on_disconnect_called = False

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
                sniffs.router.route("awaitable/function", "another message")
            )
            the_return = await _awaitable_function
            self.assertEqual(the_return, "awaitable function return value")

        asyncio.run(run_test())

    def _on_connect(self):
        self.on_connect_called = True

    def _on_disconnect(self):
        self.on_connect_called = True

    def test_arg_names_on_sync_function(self):
        assert arg_names(sync_foo) == ["a", "b", "c", "d", "e", "f"]

    def test_arg_names_on_async_function(self):
        assert arg_names(async_foo) == ["a", "b", "c", "d", "e", "f"]

    def test_arg_names_on_bound_function(self):
        assert arg_names(bound_foo) == ["a", "b", "c", "d", "e", "f"]

    def test_arg_names_on_closure(self):
        bar = 0
        def closure(a, b, c, d, e, f):
            nonlocal bar

        assert arg_names(closure) == ["a", "b", "c", "d", "e", "f"]

    # In order to properly test on_connect and on_disconnect, I would need to rewire up
    # the integration testing. Not an immediate priority, but I'll put it on the list of
    # things to do.
    #
    # def test_on_connect(self):
    #     client = sniffs.client  # reuse this client
    #     try:
    #         client.disconnect()  # make sure disconnected
    #     except:
    #         pass
    #     new_sniffs = Sniffs(on_connect=self._on_connect)
    #     new_sniffs.bind(client)
    #     client.connect()
    #     assert self.on_connect_called is True
    #
    # def test_on_disconnect(self):
    #     client = sniffs.client  # reuse this client
    #     try:
    #         client.connect()  # make sure connected
    #     except:
    #         pass
    #     new_sniffs = Sniffs(on_disconnect=self._on_disconnect)
    #     new_sniffs.bind(client)
    #     client.disconnect()
    #     assert self.on_disconnect_called is True


unittest.main()

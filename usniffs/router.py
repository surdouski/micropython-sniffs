import asyncio
import re

from usniffs.utils import arg_names, re_escape, itertools_product


LHS_VARIABLE_TOKEN = "<"
RHS_VARIABLE_TOKEN = ">"
VARIABLE_OPTIONS_DELIMITER = ":"
LHS_OPTIONS_TOKEN = "{"
RHS_OPTIONS_TOKEN = "}"
OPTIONS_DELIMITER = ","


class Router:
    def __init__(self):
        self.routes = []

    def add_route(self, topic_template_string: str, callback) -> None:
        """
        Add a route to the router.

        Args:
            topic_template_string (str): MQTT topic template to match.
            callback (Callable): Handler function to be called when a message is received on the matched topic.
        """

        template_arg_names = self._parse_template_arg_names(topic_template_string)
        func_arg_names = arg_names(callback)

        _incorrect_args = [
            arg_name
            for arg_name in func_arg_names
            if arg_name != "topic"
            and arg_name != "message"
            and arg_name not in template_arg_names
        ]
        if _incorrect_args:
            raise Exception(
                f"Arguments found in function definition that were not in routing template: {_incorrect_args}"
            )

        topic_pattern = self._parse_topic_pattern(topic_template_string)
        topic_strings = self._generate_subscription_topic_paths(topic_template_string)
        for topic_string in topic_strings:
            match = topic_pattern.match(topic_string)
            if len(template_arg_names) != len(match.groups()):
                # this should not be possible, if you see this error and are investigating, post an issue
                raise Exception(
                    "Number of parsed routing template keys were different than matched groups."
                )

            _kwargs = {
                "topic": topic_string,  # known at time of creation
                "message": "<to-be-updated>",  # will be updated later (if included in func args)
            }

            # no groupdict support in micropython
            # template_arg_names items are ordered in the same way that match.groups is
            for (
                n,
                match_value,
            ) in enumerate(match.groups()):
                _kwargs[template_arg_names[n]] = match_value

            kwargs = {
                arg: value for arg, value in _kwargs.items() if arg in func_arg_names
            }  # only use items that exist in the function signature

            route = {
                "topic_string": topic_string,  # str
                "callback": callback,  # Callable[[*list[str]],None]
                "kwargs": kwargs,  # dict[string,string|None]
            }
            self.routes.append(route)
            print(f"Added new route: {route['topic_string']}: {kwargs}")

    async def route(self, topic: str, message: str) -> tuple:
        """
        Route a received message to the appropriate handler based on the topic.

        Args:
            topic (str): MQTT topic of the received message.
            message (str): Payload of the received message.
        """
        tasks = []
        for route in self.routes:
            if route["topic_string"] == topic:
                func = route["callback"]
                kwargs = route["kwargs"]
                # only update message if it exists as True in kwargs
                if kwargs.get("message"):
                    kwargs["message"] = message
                tasks.append(func(**kwargs))
        results = await asyncio.gather(*tasks)
        return tuple(results) if results else tuple()

    def _parse_topic_pattern(self, topic_pattern: str) -> re.Pattern:
        """
        Parse MQTT topic pattern and add named capture groups automatically.

        Args:
            topic_pattern (str): MQTT topic pattern.

        Returns:
            re.Pattern: Compiled regular expression pattern.
        """
        pattern_parts = []
        for part in topic_pattern.split("/"):
            if LHS_OPTIONS_TOKEN in part and RHS_OPTIONS_TOKEN in part:
                variable_string, options_string = part.split(VARIABLE_OPTIONS_DELIMITER)
                options_string = options_string[1:-1]
                options = options_string.split(OPTIONS_DELIMITER)
                options = [option for option in options if option]
                part = f"({'|'.join(map(re_escape, options))})"
            elif part.startswith(LHS_VARIABLE_TOKEN) and part.endswith(
                RHS_VARIABLE_TOKEN
            ):
                part = f"([^/]+)"
            pattern_parts.append(part)
        pattern = "/".join(pattern_parts)
        return re.compile(pattern)

    @staticmethod
    def _parse_template_arg_names(topic_pattern: str) -> list[str]:
        """
        Parse MQTT topic pattern for variables to send back through kwargs.

        Args:
            topic_pattern (str): MQTT topic pattern.

        Returns:
            list[str]: Indexed variables, in same order as appears in topic pattern
        """
        variables = []
        for part in topic_pattern.split("/"):
            if LHS_OPTIONS_TOKEN in part and RHS_OPTIONS_TOKEN in part:
                variable_string, options_string = part.split(VARIABLE_OPTIONS_DELIMITER)
                variables.append(variable_string[1:-1])
            elif part.startswith(LHS_VARIABLE_TOKEN) and part.endswith(
                RHS_VARIABLE_TOKEN
            ):
                variables.append(part[1:-1])
        return variables

    @staticmethod
    def _generate_subscription_topic_paths(topic_pattern: str) -> list[str]:
        generated_subscription_topics = []

        parts = topic_pattern.split("/")
        variables = []
        for part in parts:
            if LHS_VARIABLE_TOKEN in part and RHS_VARIABLE_TOKEN in part:
                var_name = part.replace(LHS_VARIABLE_TOKEN, "").replace(
                    RHS_VARIABLE_TOKEN, ""
                )
                var_options = var_name.split(":")
                if len(var_options) > 1:
                    topic_pattern = topic_pattern.replace(part, var_options[0])
                    variables.append(
                        (
                            var_options[0],
                            var_options[1]
                            .strip(f"{LHS_OPTIONS_TOKEN}{RHS_OPTIONS_TOKEN}")
                            .split(","),
                        )
                    )
                else:
                    topic_pattern = topic_pattern.replace(part, var_name)
                    variables.append((var_name, ["+"]))

        combinations = itertools_product(*[options for _, options in variables])
        for combo in combinations:
            topic = topic_pattern
            for (var_name, _), val in zip(variables, combo):
                topic = topic.replace(f"{var_name}", val)
            generated_subscription_topics.append(topic)

        return generated_subscription_topics

    def get_topic_paths(self):
        return [route["topic_string"] for route in self.routes]

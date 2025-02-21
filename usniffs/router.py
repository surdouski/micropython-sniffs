import re

from usniffs.utils import arg_names, re_escape, itertools_product, match_groups
from usniffs.returns import AwaitableReturns


LV_T = "<"  # LHS VARIABLE TOKEN
RV_T = ">"  # RHS VARIABLE TOKEN

V_D = ":"   # VARIABLE DELIMITER
LO_T = "{"  # LHS OPTIONS TOKEN
RO_T = "}"  # RHS OPTIONS TOKEN
O_D = ","   # OPTIONS DELIMITER


class Router:
    def __init__(self, awaitable_returns: AwaitableReturns):
        self.routes = []
        self._awaitable_returns = awaitable_returns

    def register(self, topic_route: str, callback) -> None:
        """
        Add a route to the router.

        Args:
            topic_route (str): MQTT topic template to match.
            callback (Callable): Handler function to be called when a message is received on the matched topic.
        """
        route_arg_names = self._parse_route_args(topic_route)
        func_arg_names = arg_names(callback)

        _incorrect_args = [
            arg_name
            for arg_name in func_arg_names
            if arg_name != "topic"
            and arg_name != "message"
            and arg_name not in route_arg_names
        ]
        if _incorrect_args:
            raise Exception(
                f"Arguments found in function definition that were not in routing template: {_incorrect_args}"
            )

        topic_pattern = self._parse_topic_pattern(topic_route)
        kwargs = {arg: "<placeholder>" for arg in func_arg_names}
        route_dict = {
            "topic_pattern": topic_pattern,  # str
            "route_arg_names": route_arg_names,
            "callback": callback,  # Callable[[*list[str]],None]
            "kwargs": kwargs,  # dict[string,string|None]
            "topic_route": topic_route,
        }
        self.routes.append(route_dict)

    async def route(self, topic: str, message: str) -> tuple:
        """
        Route a received message to the appropriate handler based on the topic.

        Args:
            topic (str): MQTT topic of the received message.
            message (str): Payload of the received message.
        """
        results = []
        for route in self.routes:
            _kwargs = {
                "topic": topic,
                "message": message,
            }
            match = route["topic_pattern"].match(topic)
            is_same_number_of_subtopics = route["topic_route"].count(
                "/"
            ) == topic.count("/")
            if match and is_same_number_of_subtopics:
                for (
                    n,
                    match_value,
                ) in enumerate(match_groups(match)):
                    _kwargs[route["route_arg_names"][n]] = match_value
                func = route["callback"]
                kwargs = route["kwargs"]
                for key in kwargs.keys():
                    kwargs[key] = _kwargs[key]
                result = await func(**kwargs)
                self._awaitable_returns.trigger_awaitable_route(
                    route["topic_route"], result
                )
                results.append(result)
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
            if LO_T in part and RO_T in part:
                variable_string, options_string = part.split(V_D)
                options_string = options_string[1:-1]
                options = options_string.split(O_D)
                options = [option for option in options if option]
                part = f"({'|'.join(map(re_escape, options))})"
            elif part.startswith(LV_T) and part.endswith(
                RV_T
            ):
                part = f"([^/]+)"
            elif part == "+":
                part = "[^/]+"
            pattern_parts.append(part)
        pattern = "/".join(pattern_parts)
        return re.compile(pattern)

    @staticmethod
    def _parse_route_args(topic_pattern: str) -> list[str]:
        """
        Parse MQTT topic pattern for variables to send back through kwargs.

        Args:
            topic_pattern (str): MQTT topic pattern.

        Returns:
            list[str]: Indexed variables, in same order as appears in topic pattern
        """
        variables = []
        for part in topic_pattern.split("/"):
            if LO_T in part and RO_T in part:
                variable_string, options_string = part.split(V_D)
                variables.append(variable_string[1:-1])
            elif part.startswith(LV_T) and part.endswith(
                RV_T
            ):
                variables.append(part[1:-1])
        return variables

    @staticmethod
    def _generate_subscription_topic_paths(topic_pattern: str) -> list[str]:
        generated_subscription_topics = []
        parts = topic_pattern.split("/")  # parts => ["foo", "bar", "<variable>:{option1,option2}", "baz"]
        variables = []
        for part in parts:
            if LV_T in part and RV_T in part:
                var_options = part.split(V_D)   # var_options => ["<variable>", "{option1,option2}"]
                if len(var_options) > 1:
                    parsed_options = var_options[1].strip(LO_T).strip(RO_T).strip(" ").split(O_D)  # parsed_options => "["option1","option2"]"
                    variables.append((part, parsed_options))
                elif len(var_options) == 1:  # e.g. ["<variable>"]
                    var = var_options[0]  # var => "<variable>"
                    variables.append((var, ["+"]))

        combinations = itertools_product(*[options for _, options in variables])
        for combo in combinations:
            final_pattern = "" + topic_pattern
            for (var_name, _), val in zip(variables, combo):
                final_pattern = final_pattern.replace(f"{var_name}", f"{val}")
            generated_subscription_topics.append(final_pattern)

        return generated_subscription_topics

    def get_topic_paths(self):
        topic_paths = []
        for route in self.routes:
            topic_paths += self._generate_subscription_topic_paths(route["topic_route"])
        return topic_paths

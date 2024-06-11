# usniffs - Micropython MQTT Router

usniffs is a MQTT routing library for embedded devices, written in micropython. It provides an easy-to-use interface
for defining routes and handling incoming messages.

## Features

- Define routes with dynamic topic patterns.
- Support for named and unnamed placeholders in topic patterns.
- Uses the asynchronous MQTT client, [mqtt_as](https://github.com/peterhinch/micropython-mqtt/tree/master) written by
  Peter Hinch, as an effective and stable foundation.

## Installation

You can install usniffs from the REPL with [mip](https://docs.micropython.org/en/latest/reference/packages.html#installing-packages-with-mip).
```python
# micropython REPL
import mip
mip.install("github:surdouski/micropython-sniffs")
```

Alternatively, you can install it by using mpremote if you don't have network connectivity on device.
```bash
$ mpremote mip install github:surdouski/micropython-sniffs
```

## Usage

Important to note:
- `config['queue_len']` must be set to 1 or greater to use the asynchronous mqtt_as interface that this library requires 
- decorated route functions must be `async`

```python
import asyncio
from mqtt_as import MQTTClient, config
from usniffs import Sniffs

app = Sniffs()

@app.route('<some_root_path>/<sub_path_name>:{option_1,option_2}/log')
async def sensor_001_message(some_root_path, sub_path_name, topic, message):
    print(f"some root path: {some_root_path}")
    print(f"sub path name: {sub_path_name}")
    print(f"topic: {topic}")
    print(f"message: {message}")
    # Do something else like creating tasks, awaiting functions, etc.

@app.route('<location>:{north,south}/<options>:{option_1,option_2}/etc')
async def sensor_001_message(location, message):
    print(f"location: {location}")
    print(f"message: {message}")
    # You don't need to include all the arguments if you don't need them, just provide the names of what you need in the arguments. 
    
# See for all available config settings https://github.com/peterhinch/micropython-mqtt/blob/master/mqtt_as/README.md#mqtt-parameters
config["client_id"] = "abc-client-id"
config["ssid"] = "my_wifi_name"
config["wifi_pw"] = "my_wifi_password"
config["server"] = "mqtt_broker_host"
config["port"] = 9937
config["user"] = "mqtt_client_username"
config["password"] = "mqtt_client_password"
config["queue_len"] = 1  # queue_len is required to be 1 or more for this library
config["ssl"] = True  # Just an example of another config option you can use, be sure to read mqtt_as docs for details

async def main():
  try:
    client = MQTTClient(config)
    await app.bind(client)  # bind usniffs handling to the mqtt_as client
    await client.connect()
    
    while True:
      await asyncio.sleep(100)  # needed so that program never terminates
  
  except Exception as e:
    # This exception handling is optional, however... this pattern helps to ensure you get your debug output over the
    # serial connection before it closes. 
    import time
    import machine
    import sys
    sys.print_exception(e)
    time.sleep(1)
    machine.reset()

try:
  asyncio.run(main())
finally:
  asyncio.new_event_loop()
```

## Documentation

### Named Placeholders

Placeholders can be used in your routes. For example, `room` here is used as a placeholder
and the argument name is injected into the function arguments:

```python
@app.route("<room>:{living_room,kitchen}/temperature")
async def receive_temperature_data(room):
    if room == "living_room":
        # do something
    elif room == "kitchen":
        # do something else
```

Argument injection works by looking up the name of the placeholder, so using a different
name is the arguments will not work:

```python
# DOES NOT WORK, DO NOT DO THIS!!!
@app.route("<room>:{living_room,kitchen}/temperature")
async def receive_temperature_data(argument_one):
    ...
```

### Wildcard Placeholders

If you want to match on anything, you can create a wildcard placeholder by not specifying any placeholder options.
This example effectively matches on the topic of `+/temperature`:

```python
@app.route("<room>/temperature")
async def receive_temperature_data(room):
    ...
```

You can use any number of named and wildcard placeholders together:

```python
@app.route("<room>/<sensor>:{sensor_1,sensor_2}/<sensor_type>{temperature,humidity}")
async def receive_temperature_data(room, sensor, sensor_type):
    ...
```

### `topic` and `message`

The `topic` and `message` arguments are injected, sort of like pytest fixtures. Do not use
them as your keys in your routes, as they are reserved.

`topic` - The topic on which the message was received. This will be the _actual_ topic name,
not the templated route. For instance, a route for `<room>:{living_room,kitchen}/temperature` will
always have a topic that is one of the following: `living_room/temperature`, `kitchen/temperature`.

`message` - The message received.

```python
@app.route("<room>:{living_room,kitchen}/temperature")
async def receive_temperature_data(room, topic, message):
    ...
```

The arguments are optional, they do not need to be included in your arguments:

```python
@app.route("<room>:{living_room,kitchen}/temperature")
async def receive_temperature_data(room):
    ...
```


## Additional

- I have not yet ported the tests over from the python MQTT routing library, [sniffs](https://github.com/surdouski/sniffs).
  Will be the next thing done.


## Contributing

Contributions are welcome! Please feel free to open issues or submit pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

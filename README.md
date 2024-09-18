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

sniffs = Sniffs()

@sniffs.route('<some_root_path>/<sub_path_name>:{option_1,option_2}/log')
async def sensor_001_message(some_root_path, sub_path_name, topic, message):
    print(f"some root path: {some_root_path}")
    print(f"sub path name: {sub_path_name}")
    print(f"topic: {topic}")
    print(f"message: {message}")
    # Do something else like creating tasks, awaiting functions, etc.

@sniffs.route('<location>:{north,south}/<options>:{option_1,option_2}/etc')
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
  client = MQTTClient(config)
  await sniffs.bind(client)  # bind usniffs handling to the mqtt_as client
  await client.connect()
  
  while True:
    await asyncio.sleep(100)  # idle wait to ensure program never terminates

asyncio.run(main())
```

Additionally, you can await the returns of the decorated functions. This allows for them being used inside coroutines in 
without any issue or further setup.

In the following example, as messages come in, they are processed inside the route 
function and then return a new value. As the new values are returned, any coroutines that are currently awaiting them 
receive that new returned value.

```python
# imports can be found in previous example

@sniffs.route('+/+')  # +/+ just means it matches on any topic/subtopic pair, such as 'any/pair' or 'foo/bar'
async def some_relevant_message(message):
    some_data = mutate_data(message)  # do some conversions/calculations, if needed by your program
    return int(some_data)  # the return will be the value that is sent to the await

async def some_coroutine():
  while True:
    data = await some_relevant_message
    if data != 42:
      print('This number is not the meaning of life.')

async def another_coroutine():
  while True:
    data = await some_relevant_message
    if data < 0:
      print('Negative numbers are scary.')
          
async def main():
  client = MQTTClient(config)  # assumes config is already setup, see previous example
  await sniffs.bind(client)
  await sniffs.connect()
  
  asyncio.create_task(some_coroutine())
  asyncio.create_task(another_coroutine())
  asyncio.sleep(0)  # not technically needed because sleeping below, but we allowing the tasks to begin running here

  while True:
      await asyncio.sleep(100)  # idle wait to ensure program never terminates

asyncio.run(main())
```

In the above example, if the messages "43" and -1 were received, in order, the outputput would be
as follows:

```
This number is not the meaning of life.  # triggers for 43
This number is not the meaning of life.  # triggers for -1
Negative numbers are scary.              # triggers for -1
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

Alternatively, you can just use `+`:

```python
@app.route("+/temperature")
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


## Tests

The default micropython/unix docker image does not work, as we require the re.match.groups that exists in the rp2 port.
The Dockerfile in this repo is built in mostly the same way, except that it passes
`CFLAGS_EXTRAS=-DMICROPY_PY_RE_MATCH_GROUPS=1` in the `make` command.

To run tests, do the following.
```
# build the dockerfile
$ docker build -t micropython-unix-rp2-tests . 

# install unittest, mounting the volume locally
$ docker run --rm -v $(pwd)/lib:/root/.micropython/lib micropython-unix-rp2-tests micropython -m mip install unittest

# run the test, using the mounted volume for the unittest deps
$ docker run --rm -v $(pwd):/code -v $(pwd)/lib:/root/.micropython/lib micropython-unix-rp2-tests micropython test.py
```

If you want to edit tests, you only need to run the last command again to see results.


## Contributing

Contributions are welcome! Please feel free to open issues or submit pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

import struct
import machine
import re


async def _async_func():
    """Used to validate a type check for an async function."""
    ...


def arg_names(fun) -> list:
    """
    Due to lack of inspect that can check signature, we must dive into the bytecode
    to extract the function arguments. Written by @felixdoerre1 in the micropython discord.
    """
    if type(fun) != type(_async_func):
        raise Exception("Only bytecode functions handled")
    addr = struct.unpack("I", struct.pack("O", fun))[0]
    qstr_table = machine.mem32[machine.mem32[addr + 0x04] + 0x08]
    bytecode = machine.mem32[addr + 0x0C]

    prelude_ptr = bytecode
    prelude = machine.mem8[prelude_ptr]
    nargs = prelude & 3
    n = 0
    while (prelude & 0x80) != 0:
        prelude_ptr += 1
        prelude = machine.mem8[prelude_ptr]
        nargs |= (prelude & 4) << n
        n = n + 1

    prelude_ptr += 1
    prelude = machine.mem8[prelude_ptr]
    while (prelude & 0x80) != 0:
        prelude_ptr += 1
        prelude = machine.mem8[prelude_ptr]

    indexes = []
    for i in range(0, 1 + nargs):
        prelude = 0x80
        value = 0
        while (prelude & 0x80) != 0:
            prelude_ptr += 1
            prelude = machine.mem8[prelude_ptr]
            value = (value << 7) | (prelude & 0x7F)
        indexes.append(value)

    return [
        struct.unpack(
            "O", struct.pack("I", (machine.mem16[qstr_table + 2 * i] << 3) | 2)
        )[0]
        for i in indexes
    ][1:]


def re_escape(pattern):
    # Replacement minimal re.escape for ure compatibility
    return re.sub(r"([\^\$\.\|\?\*\+\(\)\[\\])", r"\\\1", pattern)


def itertools_product(*args, repeat=1):
    """
    Cartesian product of input iterables.

    Equivalent to itertools.product in standard Python.
    """
    # Convert args to a list of lists, each repeated 'repeat' times
    pools = [tuple(pool) for pool in args] * repeat
    result = [[]]

    # Iterate over each pool
    for pool in pools:
        # Create a new result list by appending each element of the pool
        # to each element of the current result
        result = [x + [y] for x in result for y in pool]

    # Yield each combination as a tuple
    for prod in result:
        yield tuple(prod)

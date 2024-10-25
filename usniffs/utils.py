import struct
import re
import uctypes
import sys


async def _async_func():
    """Used to validate a type check for an async function."""
    ...

def _sync_func():
    """Used to validate a type check for a sync function."""

class _FooClass:
    def bound_method(self):
        """Used to validate a type check for a bound method."""
        ...

def arg_names(fun) -> list:
    """
    Due to lack of inspect that can check signature, we must dive into the bytecode
    to extract the function arguments. Written by @felixdoerre1 in the micropython discord.
    """
    ptr = len(struct.pack("O", fun))
    addr = struct.unpack("P", struct.pack("O", fun))[0]
    def closure(x):
        nonlocal fun
    is_async_function = type(fun) == type(_async_func)
    is_sync_function = type(fun) == type(_sync_func)
    is_bound_method = type(fun) == type(_FooClass().bound_method)
    is_closure = type(fun) == type(closure)
    if is_closure:
        if sys.platform == "linux":
            desc = {
                "fun": (uctypes.UINT64 | (1 * ptr)),
                "n_closed": (uctypes.UINT32 | (2 * ptr))
            }
        else:  # Assume rp2 for now, might need to update in the future.
            desc = {
                "fun": (uctypes.UINT32 | (1 * ptr)),
                "n_closed": (uctypes.UINT32 | (2 * ptr))
            }

        fun_closure = uctypes.struct(addr, desc, uctypes.NATIVE)
        return arg_names(struct.unpack("O", struct.pack("P", fun_closure.fun))[0])[fun_closure.n_closed:]

    if not is_sync_function and not is_async_function and not is_bound_method:
        raise Exception("Only bytecode functions and bound methods are handled.")
    desc = {
        "context": (uctypes.PTR | (1 * ptr), {"qstr_table": (uctypes.PTR | 2 * ptr, uctypes.UINT16)}),
        "bytecode": (uctypes.PTR | (3 * ptr), uctypes.UINT8),
    }
    fun_bc = uctypes.struct(addr, desc, uctypes.NATIVE)
    qstr_table = fun_bc.context[0].qstr_table
    bytecode = fun_bc.bytecode

    prelude_ptr = 0
    prelude = bytecode[prelude_ptr]
    nargs = prelude & 3
    n = 0
    while (prelude & 0x80) != 0:
        prelude_ptr += 1
        prelude = bytecode[prelude_ptr]
        nargs |= (prelude & 4) << n
        n = n + 1

    prelude_ptr += 1
    prelude = bytecode[prelude_ptr]
    while (prelude & 0x80) != 0:
        print(".")
        prelude_ptr += 1
        prelude = bytecode[prelude_ptr]

    indexes = []
    for i in range(0, 1 + nargs):
        prelude = 0x80
        value = 0
        while (prelude & 0x80) != 0:
            prelude_ptr += 1
            prelude = bytecode[prelude_ptr]
            value = (value << 7) | (prelude & 0x7F)
        indexes.append(value)
    index_start = 2 if is_bound_method else 1  # Remove "self" from the args if it is a bound method.
    return [
        struct.unpack("O", struct.pack("P", (qstr_table[i] << 3) | 2))[0]
        for i in indexes
    ][index_start:]


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

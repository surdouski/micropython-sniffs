# custom micropython build for unix
FROM ubuntu:latest

RUN apt update && apt install -y gcc-multilib g++-multilib libffi-dev python3 python3-pip python3-setuptools python3-pyelftools git autoconf libtool pkg-config libsqlite3-dev

RUN rm -rf /var/lib/apt/lists/*

RUN git clone --depth 1 --branch v1.23.0 https://github.com/micropython/micropython.git

RUN make -C micropython/mpy-cross

RUN make -C micropython/ports/unix submodules

# The `CFLAGS_EXTRA=-DMICROPY_PY_RE_MATCH_GROUPS=1` is the important part of this Dockerfile.
# It adds the re.match.groups functionality to the unix build of micropython.
RUN make -C micropython/ports/unix CFLAGS_EXTRA=-DMICROPY_PY_RE_MATCH_GROUPS=1

RUN make -C micropython/ports/unix install

RUN apt-get purge --auto-remove -y build-essential git pkg-config python3

RUN rm -rf micropython

WORKDIR /code

CMD ["/usr/local/bin/micropython"]

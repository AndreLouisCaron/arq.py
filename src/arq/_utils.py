# -*- coding: utf-8 -*-


import gevent
import gevent.socket
import socket

from contextlib import (
    closing,
    contextmanager,
)


@contextmanager
def udpsocket(host='127.0.0.1', port=0):
    """Create, bind and automtically close a UDP socket."""
    s = gevent.socket.socket(
        socket.AF_INET,
        socket.SOCK_DGRAM,
        socket.IPPROTO_UDP,
    )
    with closing(s):
        s.bind((host, port))
        yield s


@contextmanager
def concurrently(function, *args, **kwds):
    """Create, schedule and automatically cancel and join a task."""
    task = gevent.spawn(function, *args, **kwds)
    try:
        yield task
    finally:
        task.kill()


__all__ = (
    'concurrently',
    'udpsocket',
)

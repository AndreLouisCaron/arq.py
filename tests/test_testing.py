# -*- coding: utf-8 -*-


import os

from arq.testing import (
    concurrently,
    udpsocket,
)


def test_concurrent_udp_peers(stack):
    """Tests can run a UDP client-server pair in parallel."""

    def echo(socket):
        """UDP echo service."""
        while True:
            data, peer = socket.recvfrom(1024)
            socket.sendto(data, peer)

    server = stack.enter_context(udpsocket())
    client = stack.enter_context(udpsocket())
    with concurrently(echo, server):
        peer = server.getsockname()
        for i in range(100):
            data = os.urandom(3)
            client.sendto(data, peer)
            d, p = client.recvfrom(1024)
            assert p == peer
            assert d == data

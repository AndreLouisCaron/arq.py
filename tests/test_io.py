# -*- coding: utf-8 -*-


import gevent
import mock
import os

from arq.testing import (
    concurrently,
    udpsocket,
)
from arq._io import (
    recvfrom,
    udp_client,
    udp_server,
)
from socket import timeout as RecvTimeout


def test_recvfrom():
    """Drop packet from unexpected peers."""

    socket = mock.MagicMock()
    socket.recvfrom.side_effect = [
        (b'abc', ('127.0.0.1', 8888)),
        (b'def', ('127.0.0.1', 9999)),
        (b'ghi', ('127.0.0.1', 7777)),
    ]

    data = recvfrom(socket, ('127.0.0.1', 7777))
    assert data == b'ghi'

    assert socket.recvfrom.call_count == 3


def test_udp_client_disconnect_timeout(stack):

    client = stack.enter_context(udpsocket())
    server = stack.enter_context(udpsocket())

    def echo(push, pull, peer):
        assert peer == str(server.getsockname())
        while True:
            push(pull())

    udp_client(
        client, echo, server.getsockname(),
        disconnect_timeout=0.001,
    )


def test_udp_client(stack):
    """UDP client can exchange packets with a server."""

    client = stack.enter_context(udpsocket())
    server = stack.enter_context(udpsocket())

    def echo(push, pull, peer):
        assert peer == str(server.getsockname())
        while True:
            push(pull())

    stack.enter_context(
        concurrently(
            udp_client,
            client, echo,
            server.getsockname(),
        )
    )

    peer = client.getsockname()
    for i in range(3):
        data = os.urandom(3)
        server.sendto(data, peer)
        assert recvfrom(server, peer) == data


def test_udp_server(stack):
    """UDP server can exchange packets with multiple clients."""

    server = stack.enter_context(udpsocket())
    clients = [
        stack.enter_context(udpsocket())
        for i in range(2)
    ]

    def echo(push, pull, peer):
        assert peer in [
            str(socket.getsockname())
            for socket in clients
        ]
        while True:
            push(pull())

    stack.enter_context(
        concurrently(
            udp_server,
            server, echo,
        )
    )

    def pound(socket):
        peer = server.getsockname()
        for i in range(3):
            data = os.urandom(3)
            socket.sendto(data, peer)
            assert recvfrom(socket, peer) == data

    tasks = [
        stack.enter_context(concurrently(
            pound, socket,
        ))
        for socket in clients
    ]
    gevent.wait(tasks, timeout=1.0)


def test_udp_server_disconnect_timeout(stack):
    """UDP server detects disconnections when clients are silent."""

    server = stack.enter_context(udpsocket())
    clients = [
        stack.enter_context(udpsocket())
        for i in range(2)
    ]

    def echo_pairs(push, pull, peer):
        """Echo, but flush only on every other packet."""
        assert peer in [
            str(socket.getsockname())
            for socket in clients
        ]
        while True:
            d1 = pull()
            d2 = pull()
            push(d1)
            push(d2)

    # Spawn the server and wait for it to finish booting.
    stack.enter_context(
        concurrently(
            udp_server,
            server, echo_pairs,
            disconnect_timeout=0.0,
        )
    )
    gevent.idle()

    def block(socket):
        """Block until the server replies."""
        socket.settimeout(0.01)
        peer = server.getsockname()
        data = os.urandom(3)
        socket.sendto(data, peer)
        try:
            assert recvfrom(socket, peer) == data
        except RecvTimeout:
            pass

    # Spawn a bunch of clients.
    tasks = [
        stack.enter_context(concurrently(
            block, socket,
        ))
        for socket in clients
    ]

    # Wait until all clients are blocked.
    gevent.idle()

    # Client will time out and return.
    assert gevent.wait(tasks, timeout=0.05) == tasks

    # NOTE: note sure how to assert that the server hanlders raised
    #       `Disconnect` and returned, but code coverage will pick it up.


def test_udp_server_never_block(stack):
    """UDP server does not block when one handler is blocked."""

    server = stack.enter_context(udpsocket())
    clients = [
        stack.enter_context(udpsocket())
        for i in range(2)
    ]
    bad_peer = str(clients[0].getsockname())

    def echo(push, pull, peer):
        """Echo, but block for one specific peer."""
        if peer == bad_peer:
            print('S:', 'bad peer', peer)
            while True:
                gevent.sleep(1.0)
        else:
            print('S:', 'good peer', peer)
            while True:
                push(pull())

    # Spawn the server and wait for it to finish booting.
    stack.enter_context(
        concurrently(
            udp_server,
            server, echo,
            max_pending_packets=1,
        )
    )
    gevent.idle()

    def pound(socket):
        host = socket.getsockname()
        peer = server.getsockname()
        socket.settimeout(0.01)
        try:
            packets = [os.urandom(3) for i in range(3)]
            for data in packets:
                print('C:', host, 'send')
                socket.sendto(data, peer)
            for data in packets:
                print('C:', host, 'recv')
                assert recvfrom(socket, peer) == data
        except RecvTimeout:
            pass

    # Spawn a bunch of clients.
    tasks = [
        stack.enter_context(concurrently(
            pound, socket,
        ))
        for socket in clients
    ]
    gevent.wait(tasks, timeout=1.0)

    # NOTE: note sure how to assert that the server dropped packets, but
    #       code coverage should pick it up.

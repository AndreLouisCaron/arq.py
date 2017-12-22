# -*- coding: utf-8 -*-


import gevent.queue
import os
import struct

from arq import (
    stop_and_wait,
)
from arq.testing import (
    concurrently,
    LossySocket,
    udpsocket,
)
from arq._io import (
    Disconnected,
    recvfrom,
)


def echo(iq, oq):
    """UDP echo service (over ARQ)."""
    while True:
        oq.put(iq.get())


def stop_and_wait_server(handler, socket, peer,
                         iq_max_size=None,
                         oq_max_size=None):
    """Start and run both the handler and the ARQ."""

    def push(data):
        return socket.sendto(data, peer)

    def pull():
        return recvfrom(socket, peer)

    iq = gevent.queue.Queue(maxsize=iq_max_size)
    oq = gevent.queue.Queue(maxsize=oq_max_size)
    with concurrently(handler, iq, oq):
        stop_and_wait(push, pull, peer, iq, oq)


def test_stop_and_wait_packet_too_small(stack, capsys):
    """Packets without at least a complete header are silently dropped."""

    server = stack.enter_context(udpsocket())
    client = stack.enter_context(udpsocket())

    stack.enter_context(
        concurrently(
            stop_and_wait_server, echo,
            server, client.getsockname(),
        )
    )

    # Wait for everything to fall into place.
    print('T: waiting for everything to become ready')
    gevent.idle()
    print('T: ready')

    # Send an invalid packet.
    peer = server.getsockname()
    data = b''
    client.sendto(data, peer)

    # Wait for the server to react.
    print('T: waiting for server to react')
    gevent.idle()
    print('T: done')

    output, errors = capsys.readouterr()
    assert errors == ''
    assert 'packet too small (size=0).' in output


def test_stop_and_wait_unexpected_ackn(stack, capsys):
    """Unexpected ACKN packets are silently dropped."""

    server = stack.enter_context(udpsocket())
    client = stack.enter_context(udpsocket())

    stack.enter_context(
        concurrently(
            stop_and_wait_server, echo,
            server, client.getsockname(),
        )
    )

    # Wait for everything to fall into place.
    print('T: waiting for everything to become ready')
    gevent.idle()
    print('T: ready')

    # Send an invalid packet.
    peer = server.getsockname()
    data = struct.pack('>BH', 0xff, 0)
    client.sendto(data, peer)

    # Wait for the server to react.
    print('T: waiting for server to react')
    gevent.idle()
    print('T: done')

    output, errors = capsys.readouterr()
    assert errors == ''
    assert 'dropping packet (invalid type 0xff).' in output


def test_stop_and_wait_iq_is_full(stack, capsys):
    """Packets are dropped when the application is not keeping up."""

    # NOTE: this will block forever because we set iq=1 to trigger the desired
    #       problem case.
    def echo_pairs(iq, oq):
        """UDP echo service (over ARQ)."""
        while True:
            d1 = iq.get()
            d2 = iq.get()
            oq.put(d1)
            oq.put(d2)

    server = stack.enter_context(udpsocket())
    client = stack.enter_context(udpsocket())

    stack.enter_context(
        concurrently(
            stop_and_wait_server, echo_pairs,
            server, client.getsockname(),
            iq_max_size=1,
        )
    )

    # Wait for everything to fall into place.
    print('T: waiting for everything to become ready')
    gevent.idle()
    print('T: ready')

    # Send a packet (should be accepted).
    peer = server.getsockname()
    data = struct.pack('>BH', 0x00, 1)
    client.sendto(data, peer)

    # Send a packet (should be dropped).
    peer = server.getsockname()
    data = struct.pack('>BH', 0x00, 2)
    client.sendto(data, peer)

    # Wait for the server to react.
    print('T: waiting for server to react')
    gevent.idle()
    print('T: done')

    output, errors = capsys.readouterr()
    assert errors == ''
    assert 'dropping data packet #2 (blocked)' in output


def test_stop_and_wait_repeat_data_packet(stack, capsys):
    """Duplicate packets in the sliding window are re-acknowledged."""

    server = stack.enter_context(udpsocket())
    client = stack.enter_context(udpsocket())

    stack.enter_context(
        concurrently(
            stop_and_wait_server, echo,
            server, client.getsockname(),
        )
    )

    # Wait for everything to fall into place.
    print('T: waiting for everything to become ready')
    gevent.idle()
    print('T: ready')

    # Send a packet (should be accepted).
    peer = server.getsockname()
    data = struct.pack('>BH', 0x00, 1)
    client.sendto(data, peer)

    # Retransmit the packet (should be dropped).
    client.sendto(data, peer)

    # Wait for the server to react.
    print('T: waiting for server to react')
    gevent.idle()
    print('T: done')

    output, errors = capsys.readouterr()
    assert errors == ''
    assert 'dropping data packet #1 (repeat)' in output


def test_stop_and_wait_data_packet_out_of_sequence(stack, capsys):
    """Data packets out of the sliding window are silently discarded."""

    server = stack.enter_context(udpsocket())
    client = stack.enter_context(udpsocket())

    stack.enter_context(
        concurrently(
            stop_and_wait_server, echo,
            server, client.getsockname(),
        )
    )

    # Wait for everything to fall into place.
    print('T: waiting for everything to become ready')
    gevent.idle()
    print('T: ready')

    # Send a packet (should be dropped).
    peer = server.getsockname()
    data = struct.pack('>BH', 0x00, 128)
    client.sendto(data, peer)

    # Wait for the server to react.
    print('T: waiting for server to react')
    gevent.idle()
    print('T: done')

    output, errors = capsys.readouterr()
    assert errors == ''
    assert 'dropping data packet #128 (out of sequence)' in output


def test_stop_and_wait_ackn_packet_out_of_sequence(stack, capsys):
    """ACKN packets out of the sliding window are silently discarded."""

    server = stack.enter_context(udpsocket())
    client = stack.enter_context(udpsocket())

    stack.enter_context(
        concurrently(
            stop_and_wait_server, echo,
            server, client.getsockname(),
        )
    )

    # Wait for everything to fall into place.
    print('T: waiting for everything to become ready')
    gevent.idle()
    print('T: ready')

    # Send a DATA packet (required to unblock peer's sender).
    peer = server.getsockname()
    data = struct.pack('>BH', 0x00, 0x0001)
    client.sendto(data, peer)

    # Send a ACKN packet (out of sequence, should be dropped).
    peer = server.getsockname()
    data = struct.pack('>BH', 0x01, 0x000f)
    client.sendto(data, peer)

    # Wait for the server to react.
    print('T: waiting for server to react')
    gevent.idle()
    print('T: done')

    output, errors = capsys.readouterr()
    assert errors == ''
    assert 'dropping ackn packet #15 (out of sequence)' in output


def test_stop_and_wait(stack):
    """Stop-and-wait client can reliably receive data."""

    server = stack.enter_context(udpsocket())
    client = stack.enter_context(udpsocket())

    # Simulate lossy networks.
    server = LossySocket(server, loss_rate=0.25)
    client = LossySocket(client, loss_rate=0.25)

    stack.enter_context(
        concurrently(
            stop_and_wait_server, echo,
            server, client.getsockname(),
        )
    )

    peer = server.getsockname()

    def push(data):
        return client.sendto(data, peer)

    def pull():
        return recvfrom(client, peer)

    iq = gevent.queue.Queue()
    oq = gevent.queue.Queue()
    stack.enter_context(
        concurrently(
            stop_and_wait,
            push,
            pull,
            peer,
            iq, oq,
        )
    )

    for i in range(100):
        data = os.urandom(3)
        oq.put(data)
        d = iq.get()
        assert d == data


def test_stop_and_wait_disconnected(stack):
    """Stop-and-wait returns when disconnected."""

    server = stack.enter_context(udpsocket())
    client = stack.enter_context(udpsocket())

    peer = server.getsockname()

    def push(data):
        return client.sendto(data, peer)

    def pull():
        raise Disconnected

    iq = gevent.queue.Queue()
    oq = gevent.queue.Queue()
    stop_and_wait(
        push,
        pull,
        peer,
        iq, oq,
    )

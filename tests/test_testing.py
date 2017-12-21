# -*- coding: utf-8 -*-


import gevent
import mock
import os
import pytest

from arq.testing import (
    concurrently,
    LossySocket,
    udpsocket,
)
from socket import timeout as RecvTimeout


def test_concurrently(stack):
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


def test_lossy_socket_endpoint(stack):
    socket = stack.enter_context(udpsocket())
    lossy_socket = LossySocket(socket, loss_rate=0.0)
    assert lossy_socket.getsockname() == socket.getsockname()


def test_lossy_socket_io(stack):
    server = stack.enter_context(udpsocket())
    client = stack.enter_context(udpsocket())
    client = LossySocket(client, loss_rate=0.0)

    data = os.urandom(3)
    client.sendto(data, server.getsockname())
    d, p = server.recvfrom(1024)
    assert d == data
    assert p == client.getsockname()


def test_lossy_socket_disable_loss():
    """No packets are lost when loss rate is zero."""

    packet = (b'', ('127.0.0.1', 8000))
    socket = mock.MagicMock()
    socket.recvfrom.return_value = packet

    s = LossySocket(socket, loss_rate=0.0)
    for i in range(1000):
        assert s.recvfrom(1024) == packet
    assert socket.recvfrom.call_count == 1000


@pytest.mark.parametrize('loss_rate', [
    0.1,
    0.25,
    0.5,
    0.75,
])
@pytest.mark.parametrize('timeout', [
    None,
    15.0,
])
def test_lossy_socket(loss_rate, timeout):
    """Packets are lost at the requested rate."""

    packet = (b'', ('127.0.0.1', 8000))
    socket = mock.MagicMock()
    socket.recvfrom.return_value = packet

    s = LossySocket(socket, loss_rate=loss_rate)
    s.settimeout(timeout)
    for i in range(1000):
        assert s.recvfrom(1024) == packet

    # Expected number of calls is computed using hyper-geometric distribution.
    keep_rate = 1.0 - loss_rate
    expected_drops = ((1.0 - keep_rate) / keep_rate)
    expected_calls = 1000 * (1.0 + expected_drops)

    # The estimation error should be less than 10%.
    error_rate = abs(
        socket.recvfrom.call_count - expected_calls) / expected_calls
    assert error_rate < 0.1


def test_lossy_socket_timeout_no_loss():
    """Recv timeout is respected when loss rate is zero."""

    e = RecvTimeout()
    socket = mock.MagicMock()
    socket.recvfrom.side_effect = e

    s = LossySocket(socket, loss_rate=0.0)
    s.settimeout(0.0)
    with pytest.raises(RecvTimeout) as exc:
        print(s.recvfrom(1024))
    assert exc.value is e


def test_lossy_socket_timeout_with_loss():
    """Recv timeout is respected when loss rate is non-zero."""

    def mock_recvfrom(size):
        gevent.sleep(0.1)

    socket = mock.MagicMock()
    socket.recvfrom.side_effect = mock_recvfrom

    s = LossySocket(socket, loss_rate=0.99)
    s.settimeout(0.0)
    with pytest.raises(RecvTimeout):
        print(s.recvfrom(1024))

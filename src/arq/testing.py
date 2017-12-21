# -*- coding: utf-8 -*-


import gevent
import random
import socket

from ._utils import (
    concurrently,
    udpsocket,
)


class LossySocket(object):
    """Socket that simulates packet loss. """

    def __init__(self, socket, loss_rate):
        assert 0.0 <= loss_rate < 1.0
        self._socket = socket
        self._timeout = None
        self._loss_rate = loss_rate

    def recvfrom(self, size):
        """Block until we receive a packet from the network.

        This method simulates lossy networks by randomly dropping incoming
        packets.

        The read will time out if no packet is received/accepted before the
        timeout is reached.
        """
        if self._timeout is None:
            while True:
                data, peer = self._socket.recvfrom(size)
                if random.random() < self._loss_rate:
                    continue
                return data, peer
        try:
            with gevent.Timeout(self._timeout):
                while True:
                    data, peer = self._socket.recvfrom(size)
                    if random.random() < self._loss_rate:
                        continue
                    return data, peer
        except gevent.Timeout:
            raise socket.timeout

    def sendto(self, data, peer):
        return self._socket.sendto(data, peer)

    def getsockname(self):
        return self._socket.getsockname()

    def settimeout(self, timeout):
        self._timeout = timeout


__all__ = (
    'concurrently',
    'LossySocket',
    'udpsocket',
)

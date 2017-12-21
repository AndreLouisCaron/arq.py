# -*- coding: utf-8 -*-


import attr
import gevent
import gevent.queue

from attr.validators import instance_of
from datetime import timedelta
from socket import timeout as RecvTimeout


from ._utils import (
    to_seconds,
)


MAX_PACKET_SIZE = 1024


@attr.s(frozen=True)
class Session(object):
    """State of a session (for one peer)."""
    q = attr.ib(validator=instance_of(gevent.queue.Queue))
    peer = attr.ib(validator=instance_of(tuple))
    task = attr.ib(validator=instance_of(gevent.Greenlet))


def recvfrom(socket, peer):
    """Receive a packet from a designated peer."""
    data, p = socket.recvfrom(MAX_PACKET_SIZE)
    while p != peer:
        data, p = socket.recvfrom(MAX_PACKET_SIZE)
    return data


class Disconnected(Exception):
    """Raised when the disconnection timeout is reached."""
    pass


def udp_client(socket, handler, peer,
               disconnect_timeout=timedelta(seconds=15)):
    """Exchange packets with a single peer."""

    disconnect_timeout = to_seconds(disconnect_timeout)

    socket.settimeout(disconnect_timeout)

    def push(data):
        """Send a packet to the peer (unreliable)."""
        socket.sendto(data, peer)

    def pull():
        """Block until we receive a packet from the peer."""
        try:
            return recvfrom(socket, peer)
        except RecvTimeout:
            raise Disconnected

    try:
        return handler(push, pull, str(peer))
    except Disconnected:
        return


def udp_server(socket, handler,
               max_pending_packets=None,
               disconnect_timeout=timedelta(seconds=15)):
    """Exchange packets with multiple peers."""

    disconnect_timeout = to_seconds(disconnect_timeout)

    sessions = {}

    def execute_handler(peer, q):
        """Automatically unregister when the handler completes."""
        try:
            def push(data):
                """Send a packet to the peer (unreliable)."""
                socket.sendto(data, peer)

            def pull():
                """Block until we receive a packet from the peer."""
                try:
                    return q.get(timeout=disconnect_timeout)
                except gevent.queue.Empty:
                    raise Disconnected

            return handler(push, pull, str(peer))
        except Disconnected:
            pass
        finally:
            del sessions[peer]

    def register_session(peer):
        """Create a new session (given a peer's endpoint)."""
        q = gevent.queue.Queue(
            maxsize=max_pending_packets,
        )
        return sessions.setdefault(peer, Session(
            peer=peer,
            q=q,
            task=gevent.spawn(execute_handler, peer, q),
        ))

    try:
        while True:
            # Receive a packet from any peer.
            #
            # TODO: remove session for handlers that have terminated.
            data, peer = socket.recvfrom(MAX_PACKET_SIZE)

            # Lookup the session (creating a new one if necessary).
            session = sessions.get(peer, None)
            if session is None:
                session = register_session(peer)

            # Dispatch the packet.
            #
            # NOTE: blocking here on one peer would prevent us from dispatching
            #   packets to other peers.  We can never let that happen as it
            #   would allow one slow session to create a denial of service to
            #   other sessions.  It is each session's responsibility to keep
            #   up with incoming traffic (or suffer data loss).
            try:
                session.q.put_nowait(data)
            except gevent.queue.Full:
                print(
                    'S:',
                    'dropping packet from %r (blocked)' % (
                        peer,
                    ),
                )
    finally:
        gevent.killall(tuple(
            s.task for s in sessions.values()
        ))

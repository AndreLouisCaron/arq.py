# -*- coding: utf-8 -*-


import gevent.queue
import itertools
import struct

from datetime import timedelta

from ._io import (
    Disconnected,
)
from ._serial import distance
from ._utils import (
    concurrently,
    to_seconds,
)


HEADER = struct.Struct('>BH')
HEADER_SIZE = HEADER.size

DATA = 0
ACKN = 1


def sequence_numbers():
    """Generate sequence numbers that wrap around."""
    for i in itertools.count(start=1):  # pragma: no branch
        yield i % 0xffff


def stop_and_wait(push, pull, peer, iq, oq,
                  retransmit_delay=timedelta(milliseconds=10)):
    """Stop-and-wait ARQ.

    This is the most basic implementation of the sliding window protocol, with
    both the send and receive windows having a size of 1.  In short, the sender
    sends one packet, then stops and waits until the receiver acknowledges the
    packet (the sender retransmits if necessary to work around data loss).

    The protocol gurantees ordering and reliability, but it is very slow
    because it requires a full round-trip for each packet (at a minimum).

    You should ensure ``iq`` and ``oq`` are bounded so that that back-pressure
    is applied.  Without proper support for back-pressure:

    - a peer can create a denial of service by sending many packets very
      quickly (memory will build-up in ``iq``);
    - the application can create a denial of service by sending many packets
      very quickly (memory will build-up in ``oq``).

    """

    aq = gevent.queue.Queue()

    # NOTE: ideally, this should be >= RTT to avoid unnecessary retransmits.
    retransmit_delay = to_seconds(retransmit_delay)

    def recv():
        for i in sequence_numbers():  # pragma: no branch
            while True:
                data = pull()
                if len(data) < HEADER.size:
                    print('recv:', 'packet too small (size=%d).' % (
                        len(data),
                    ))
                    continue
                t, j = HEADER.unpack(data[:HEADER.size])
                if t == DATA:
                    if j == i:
                        # NOTE: if we were to block here (e.g. because the
                        #   application is slow to process inbound packets),
                        #   then we would no longer be able to receive ACKN
                        #   packets.  Make sure we *never* block here.
                        try:
                            iq.put_nowait(data[HEADER.size:])
                        except gevent.queue.Full:
                            print(
                                'recv:',
                                'dropping data packet #%d (blocked)' % (
                                    j,
                                ),
                            )
                            pass
                        else:
                            push(HEADER.pack(ACKN, i))
                            break
                    elif distance(i, j) <= 1:
                        print(
                            'recv:',
                            'dropping data packet #%d (repeat)' % (
                                j,
                            )
                        )
                        push(HEADER.pack(ACKN, j))
                    else:
                        print(
                            'recv:',
                            'dropping data packet #%d (out of sequence).' % (
                                j,
                            )
                        )
                elif t == ACKN:
                    aq.put(j)
                else:
                    print(
                        'recv:',
                        'dropping packet (invalid type 0x%02x).' % (
                            t,
                        ),
                    )

    def send():
        for i in sequence_numbers():  # pragma: no branch
            data = oq.get()
            head = HEADER.pack(DATA, i)
            push(head + data)
            # Wait for the acknowledgement, retransmitting periodically.
            while True:
                try:
                    j = aq.get(timeout=retransmit_delay)
                except gevent.queue.Empty:
                    push(head + data)
                    continue
                if distance(i, j) == 0:
                    break
                else:
                    print(
                        'send:',
                        'dropping ackn packet #%d (out of sequence)' % (
                            j,
                        ),
                    )

    with concurrently(send):
        try:
            recv()
        except Disconnected:
            return


__all__ = (
    'stop_and_wait',
)

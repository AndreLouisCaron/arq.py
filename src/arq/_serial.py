# -*- coding: utf-8 -*-


def distance(i, j):
    """Compute distance from ``j`` to ``i`` (with wrap-around).

    This is implemented as a very fast algorithm that breaks down if the
    sequence numbers are too far apart (in which case they can appear to have
    small distances).  In practice, this allows sliding windows that are large
    enough for many applications.  For example, with 16-bit sequence numbers,
    it allows sliding windows up to 0x4000 (16384) packets.

    It is the protocol's responsibility to ensure that such large differences
    in sequence numbers never occur (e.g. by configuring the ARQ to never use a
    sliding window that large).  Of course, a malicious attacker could try to
    craft packets with sequence numbers in the range that conflicts with the
    current sliding window.  If security is of concern, you should protect the
    packet with some form of cryptography to ensure a malicious attacker cannot
    craft packets at all.

    """
    return ((i - j) & 0x7fff)

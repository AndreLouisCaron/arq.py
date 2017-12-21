.. -*- encoding: utf-8 -*-

=======================================================
  arq.py: ARQ implementations in Python, using Gevent
=======================================================

Description
===========

This project is a training exercise.  It's intended to help me learn about
reliable data transfers by implementing various ARQ_ protocols.  I'm writing
them in Python to learn more about concurrency in Gevent.

The code is meant to be more readable than reliable or performant.  Please do
not use this to build a DIY TCP-over-UDP in any serious application :-)

.. _ARQ: https://en.wikipedia.org/wiki/Automatic_repeat_request

ARQ Implementations
===================

Stop and wait
-------------

The `Stop-and-wait ARQ`_ is the simplest of all.  The receive emits and ACK
packet upon reception of a data packet.  The sender retransmits outbound
packets at regular intervals until it receives and acknowledgement from its
peer.

.. _`Stop-and-wait ARQ`: https://en.wikipedia.org/wiki/Stop-and-wait_ARQ

License
=======

MIT license, see ``LICENSE`` file.


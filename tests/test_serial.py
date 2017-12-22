# -*- coding: utf-8 -*-


import pytest

from arq._serial import distance


@pytest.mark.parametrize('i,j,d', [
    # simple distance.
    (7, 2, 5),
    (3, 2, 1),
    (2, 1, 1),
    (1, 0, 1),
    # distance in presence of wrapping.
    (0, 0xffff, 1),
    (1, 0xffff, 2),
    (0, 0xfffe, 2),
    # negative range (distance value is not accurate, but much higher than N)
    (2, 3, 0x7fff),
    # very large distance (breaks down here, protocol must avoid this)
    (2, 0x7fff, 3),
])
def test_distance(i, j, d):
    assert distance(i, j) == d

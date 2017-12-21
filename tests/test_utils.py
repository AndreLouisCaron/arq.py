# -*- coding: utf-8 -*-


import pytest

from arq._utils import to_seconds
from datetime import timedelta


@pytest.mark.parametrize('timeout,seconds', [
    (1.0, 1.0),
    (timedelta(seconds=1), 1.0),
])
def test_to_seconds(timeout, seconds):
    assert to_seconds(timeout) == seconds

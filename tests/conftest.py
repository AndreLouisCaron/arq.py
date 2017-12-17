# -*- coding: utf-8 -*-


import pytest

from contextlib2 import ExitStack


@pytest.fixture(scope='function')
def stack():
    """Provide a cleanup stack to use in the test (without indentation)."""
    with ExitStack() as stack:
        yield stack

import pytest

from shepherd_core import get_verbose_level
from shepherd_core import set_verbose_level


@pytest.mark.parametrize("log_level", range(-5, 10))
def test_log_levels(log_level: int) -> None:
    set_verbose_level(log_level)
    if log_level <= 0:
        assert get_verbose_level() == 0
    elif log_level <= 3:
        assert get_verbose_level() == log_level
    else:
        assert get_verbose_level() == 3

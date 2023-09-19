import pytest

from shepherd_core import get_verbose_level
from shepherd_core import increase_verbose_level


@pytest.mark.parametrize("log_level", range(-5, 10))
def test_log_levels(log_level: int) -> None:
    increase_verbose_level(log_level)
    if log_level <= 2:
        assert get_verbose_level() == 2
    elif log_level <= 3:
        assert get_verbose_level() == log_level
    else:
        assert get_verbose_level() == 3

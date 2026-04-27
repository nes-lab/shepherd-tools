"""Base-set of bounding math functions."""

from shepherd_core.logger import log

U32_MAX: int = 2**32 - 1
U64_MAX: int = 2**64 - 1


def u32s(i: float) -> int:
    """Guard to supervise calculated model-states."""
    if i > U32_MAX:
        log.warning("u32-overflow")
    if i < 0:
        log.warning("u32-underflow")
    return int(min(max(i, 0), 2**32 - 1))


def u64s(i: float) -> int:
    """Guard to supervise calculated model-states."""
    if i > U64_MAX:
        log.warning("u64-overflow")
    if i < 0:
        log.warning("u64-underflow")
    return int(min(max(i, 0), 2**64 - 1))


def mul64(value1: float, value2: float) -> int:
    """Bind result of multiplication to uint64_t-range."""
    return min(int(value1 * value2), U64_MAX)


def mul32(value1: float, value2: float) -> int:
    """Bind result of multiplication to uint32_t-range."""
    return min(int(value1 * value2), U32_MAX)


def mul32e(value1: float, value2: float) -> int:
    """Bind result of multiplication to uint64_t-range."""
    return min(int(value1 * value2), U64_MAX)


def add64(value1: float, value2: float) -> int:
    """Bind result of addition to uint64_t-range."""
    return min(int(value1 + value2), U64_MAX)


def add32(value1: float, value2: float) -> int:
    """Bind result of addition to uint32_t-range."""
    return min(int(value1 + value2), U32_MAX)


def add32s(value1: float, value2: float) -> int:
    """Bind result of signed addition to uint32_t-range."""
    return max(min(int(value1 + value2), U32_MAX), 0)


def sub64(value1: float, value2: float) -> int:
    """Bind result of subtraction to uint64_t-range."""
    return max(int(value1 - value2), 0)


def sub32(value1: float, value2: float) -> int:
    """Bind result of subtraction to uint32_t-range."""
    return max(int(value1 - value2), 0)


def sub32s(value1: float, value2: float) -> int:
    """Bind result of signed subtraction to uint32_t-range."""
    return max(min(int(value1 - value2), U32_MAX), 0)

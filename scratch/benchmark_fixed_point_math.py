"""A simple benchmark to get a feeling for the best approach in python."""

import random
import timeit
from collections.abc import Callable

random.seed(42)
DATA: list[int] = [random.randint(0, 10000) for _ in range(400)]


def measure(func: Callable, name: str) -> None:
    """Benchmark that runs function and times it."""
    time = timeit.timeit(lambda: [func(val) for val in DATA], number=500_000)
    print(f"It took {time}s for {name}")


measure(lambda x: x / 2, "division by 2")
measure(lambda x: x // 2, "integer division by 2")
measure(lambda x: x >> 1, "shift by 1")

measure(lambda x: x / 4, "division by 4")
measure(lambda x: x // 4, "integer division by 4")
measure(lambda x: x >> 2, "shift by 2")

measure(lambda x: x / 256, "division by 256")
measure(lambda x: x // 256, "integer division by 256")
measure(lambda x: x >> 8, "shift by 8")

# result: last two (integer with larger div) are ~ 20% faster

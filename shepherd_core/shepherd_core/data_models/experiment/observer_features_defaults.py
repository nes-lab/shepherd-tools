"""Pre-init complex types for improved perf."""

from .observer_features import GpioTracing
from .observer_features import PowerTracing
from .observer_features import SystemLogging
from .observer_features import UartLogging

power_tracer_default = PowerTracing()
gpio_tracing_default = GpioTracing()
uart_logging_default = UartLogging()
sys_logging_all = SystemLogging()  # = all active

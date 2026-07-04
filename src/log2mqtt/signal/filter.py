from __future__ import annotations

from abc import ABC, abstractmethod
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from log2mqtt.sensor import Pattern, Sensor

class Filter(ABC):
    def __init__(self, event_value: float, *, owner: Pattern|Sensor|None = None, initial_value: float = 0.0, initial_time: float|None = None):
        self.event_value = event_value
        self.y_prev = initial_value
        self.last_time = time.monotonic() if initial_time is None else initial_time
        self._owner = owner

    @abstractmethod
    def process_event(self, x_new: float, current_time: float|None = None) -> float:
        pass

    @property
    def owner(self) -> Pattern|Sensor|None:
        return self._owner

    @property
    def signal(self) -> float:
        return self.process_event(0.0)

    def record_event(self) -> float:
        return self.process_event(self.event_value)
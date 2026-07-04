from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from log2mqtt.activity import Activity
    from log2mqtt.sensor import Sensor


class ActivityObserver(ABC):
    """An observer that receives activity status updates from an ActivitySubject."""

    @abstractmethod
    def update(self, sensor: "Sensor", activity: Activity | None, signal: float) -> None:
        """Handle an activity update from a subject."""
        ...


class ActivitySubject(ABC):
    """A subject that can attach observers and notify them of activity updates."""

    def __init__(self) -> None:
        self._activity_observers: list[ActivityObserver] = []

    def register_observer(self, observer: ActivityObserver) -> None:
        """Register an observer to receive activity updates."""
        if observer not in self._activity_observers:
            self._activity_observers.append(observer)

    def unregister_observer(self, observer: ActivityObserver) -> None:
        """Unregister an observer from receiving activity updates."""
        if observer in self._activity_observers:
            self._activity_observers.remove(observer)

    def notify_observers(self, sensor: "Sensor", activity: Activity | None, signal: float) -> None:
        """Notify all registered observers of an activity update."""
        for observer in list(self._activity_observers):
            observer.update(sensor, activity, signal)

from datetime import datetime, timedelta
import logging
from typing import Dict
from uuid import UUID

from log2mqtt.sensor import Sensor
from log2mqtt.activity_observer import ActivityObserver
from log2mqtt.activity import Activity

class AggregateSensor(Sensor, ActivityObserver):

    def __init__(self, name: str | None = None, subject_type: str | None = None, strategy: str = "latest"):
        self._current_component = None
        self._strategy = strategy
        self._stack = []
        super().__init__(name, subject_type)
        
    def update(self, sensor: Sensor, activity: Activity | None, signal: float) -> None:
        top_activity = None
        if self._strategy == "latest":
            if self._stack is None: self._stack = []
            self._stack = [t for t in self._stack if t[0] != sensor and t[1] is not None]
            if activity is not None or len(self._stack) <= 0: self._stack.append((sensor, activity))
            # Stack will always have at least one item, latest non-None or just arrived None
            top_activity = self._stack[-1][1]
            self._current_component = self._stack[-1][0]
        if self._strategy == "priority":
            for s in self._priority_list:
                a = activity if s == sensor else s.current_activity # just in case there's update lag for some reason
                if a is not None:
                    top_activity = a
                    self._current_component = s
                    break
        self._set_activity(top_activity, 1.0)

    def set_priority(self, sensors: list[Sensor] = []):
        self._priority_list = sensors

    #TODO: If we didn't break LSP already then we probably have now... refactor?
    def update_state(self, force: bool = False):
        pass # Override parent method that calls _decay()

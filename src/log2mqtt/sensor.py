from datetime import datetime, timedelta
import logging
from typing import Dict
from uuid import UUID

from log2mqtt.activity_observer import ActivitySubject
from log2mqtt.activity import Activity, Pattern
from log2mqtt.signal.filter import Filter

DEFAULT_CUTOFF=1/10.0

logger = logging.getLogger(__name__)

class Sensor(ActivitySubject):

    def __init__(self, name: str|None = None, subject_type: str|None = None):
        super().__init__()
        self._name = name
        self._subject_type = subject_type
        self._last_event_at = datetime.now()
        self._last_update_at = datetime.now()
        self._current_activity = None
        self._pattern_filters: Dict[UUID, Filter] = {} # key: Pattern.id
        self._known_activities: Dict[UUID, Activity] = {} # key: Activity.id
        self._pattern_activities: Dict[UUID, UUID] = {} # key: Pattern.id, value: Activity.id

    @property
    def name(self):
        return self._name
    
    @property
    def subject_type(self):
        return self._subject_type
    
    def record_event(self, activity: Activity, pattern: Pattern):
        """
        Called when a new pattern match has been observed relevant to this sensor.
        """

        # Update self._last_event_at
        self._last_event_at = datetime.now() #TODO: Move now capture further up?

        # If activity not in _known_activities, add it
        if activity.id not in self._known_activities:
            self._known_activities[activity.id] = activity

        if pattern.id not in self._pattern_filters:
            self._pattern_filters[pattern.id] = pattern.filter_factory()
            self._pattern_activities[pattern.id] = activity.id

        self._decay()

        # Record a "hit" on the pattern
        filter_instance = self._pattern_filters[pattern.id]
        signal_value = filter_instance.record_event()
        activity_name = self._known_activities[self._pattern_activities[pattern.id]].name
        logger.debug(f"Sensor {self.name} got a {activity_name} signal value of {signal_value:.3f}")

        a, signal = self._determine_activity()

        self._set_activity(a, signal)

    def _decay(self):
        for p_id, filter_instance in list(self._pattern_filters.items()):
            owner = filter_instance.owner
            if owner is None:
                del self._pattern_filters[p_id]
                continue

            echo_value = filter_instance.signal # handles time-based decay
            activity_id = self._pattern_activities.get(p_id)
            activity_name = self._known_activities[activity_id].name if activity_id in self._known_activities else '<Unknown>'
            logger.debug(f"Sensor {self.name} got a {activity_name} echo value of {echo_value:.3f}")
    
    def _determine_activity(self) -> tuple[Activity|None, float]:
        top = (0.0, None)
        for p_id, filter_instance in list(self._pattern_filters.items()):
            echo_value = filter_instance.signal
            if echo_value > top[0]:
                top = (echo_value, p_id)
        self._last_update_at = datetime.now()
        if top[1] is None:
            return None, 0.0
        if top[0] < DEFAULT_CUTOFF:
            self._cleanup()
            return None, top[0]
        return self._known_activities[self._pattern_activities[top[1]]], top[0]

    def _set_activity(self, activity: Activity|None, signal: float):
        self._current_activity = activity
        logger.info(f"Sensor {self._name or '<Unnamed>'} set activity {activity.name if activity else '<None>'}")
        self.notify_observers(self, activity, signal)

    def _cleanup(self):
        self._known_activities = {}
        self._pattern_filters = {}
        self._pattern_activities = {}

    def update_state(self, force: bool = False):

        if not force:
            maxwait = 1.0 #TODO: Make period configurable?
            if self._last_update_at + timedelta(seconds=maxwait) > datetime.now():
                return self._current_activity

        self._decay()

        a, signal_value = self._determine_activity()
        if a != self._current_activity:
            self._set_activity(a, signal_value)


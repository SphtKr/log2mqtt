from datetime import datetime, timedelta
import logging
from typing import Dict
from uuid import UUID

from log2mqtt.activity import Activity, Pattern
from log2mqtt.signal.rc import AsymmetricRCFilter

DEFAULT_GAIN=1.0
DEFAULT_REVERB=0.5 # signal retains 0.5 * its rmaining "volume" for every second passed
DEFAULT_CUTOFF=1/10.0

logger = logging.getLogger(__name__)

class Sensor:

    def __init__(self, name: str|None = None):
        self._name = name
        self._last_event_at = datetime.now()
        self._last_update_at = datetime.now()
        self._current_activity = None
        self._pattern_filters: Dict[UUID, AsymmetricRCFilter] = {} # key: Pattern.id
        # self._pattern_echoes: Dict[UUID, float] = {} # key: Pattern.id
        self._known_patterns: Dict[UUID, Pattern] = {} # key: Pattern.id
        self._known_activities: Dict[UUID, Activity] = {} # key: Activity.id
        self._pattern_activities: Dict[UUID, UUID] = {} # key: Pattern.id, value: Activity.id

    @property
    def name(self):
        return self._name
    
    def record_event(self, activity: Activity, pattern: Pattern):
        """
        Called when a new pattern match has been observed relevant to this sensor.
        """

        # Update self._last_event_at
        self._last_event_at = datetime.now() #TODO: Move now capture further up?

        # If activity not in _known_activities, add it
        if activity.id not in self._known_activities:
            self._known_activities[activity.id] = activity

        # If pattern not in _known_patterns, add it, and add the pattern.id and activity.id to _pattern_activities
        if pattern.id not in self._known_patterns:
            self._known_patterns[pattern.id] = pattern
            self._pattern_filters[pattern.id] = pattern.filter_factory()
            self._pattern_activities[pattern.id] = activity.id
        
        self._decay()

        # Record a "hit" on the pattern
        signal_value = self._pattern_filters[pattern.id].record_event()
        logger.debug(f"Sensor {self.name} got a {self._known_activities[self._pattern_activities[pattern.id]].name} signal value of {signal_value:.3f}")

        a = self._determine_activity()

        self._set_activity(a)

    def _decay(self):
        for p_id, echo_value in list(self._pattern_filters.items()):
            p = self._known_patterns.get(p_id, None)
            if p:
                echo_value = self._pattern_filters[p_id].signal # handles time-based decay
                logger.debug(f"Sensor {self.name} got a {self._known_activities[self._pattern_activities[p_id]].name} echo value of {echo_value:.3f}")
            else:
                # If for some reason the pattern is no longer known, remove the filter
                del self._pattern_filters[p_id]
    
    def _determine_activity(self) -> Activity|None:
        top = (0, None)
        for p_id, filter in list(self._pattern_filters.items()):
            echo_value = filter.signal
            if echo_value > top[0]:
                top = (echo_value, p_id)
        self._last_update_at = datetime.now()
        if top[1] is None:
            return None
        if top[0] < DEFAULT_CUTOFF:
            self._cleanup()
            return None
        else:
            return self._known_activities[self._pattern_activities[top[1]]]

    def _set_activity(self, activity: Activity|None):
        self._current_activity = activity
        logger.info(f"Sensor {self._name or '<Unnamed>'} set activity {activity.name if activity else '<None>'}")
        ...

    def _cleanup(self):
        self._known_patterns = {}
        self._known_activities = {}
        self._pattern_filters = {}
        self._pattern_activities = {}

    def update_state(self, force: bool = False):

        if not force:
            maxwait = 1.0 #TODO: Make period configurable?
            if self._last_update_at + timedelta(seconds=maxwait) > datetime.now():
                return self._current_activity

        self._decay()

        a = self._determine_activity()
        if a != self._current_activity:
            self._set_activity(a)


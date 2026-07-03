from datetime import datetime, timedelta
import logging
from typing import Dict
from uuid import UUID

from log2mqtt.activity import Activity, Pattern

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
        self._pattern_echoes: Dict[UUID, float] = {} # key: Pattern.id
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
            self._pattern_activities[pattern.id] = activity.id
        
        self._decay()

        # Set the _pattern_echoes value of the provided pattern to equal pattern.gain
        self._pattern_echoes[pattern.id] = pattern.gain

        a = self._determine_activity()

        self._set_activity(a)

    def _decay(self):
        # Loop through all the _pattern_echoes, multiplying their last stored "echo" value by
        # the Pattern's reverb value raised to the number of seconds since _last_update_at
        now = datetime.now()
        seconds_passed = (now - self._last_update_at).total_seconds()
        
        to_drop = []
        for p_id, echo_value in list(self._pattern_echoes.items()):
            # We need the pattern to get its reverb value
            p = self._known_patterns.get(p_id)
            if p:
                echo_value = echo_value * (p.reverb_factor ** seconds_passed)
                if echo_value < DEFAULT_CUTOFF:
                    to_drop.append(p_id)
                else:
                    self._pattern_echoes[p_id] = echo_value
                    logger.debug(f"Sensor {self.name} reduced a {self._known_activities[self._pattern_activities[p_id]].name} echo value to {echo_value:.3f}")
            else:
                # If for some reason the pattern is no longer known, remove the echo
                del self._pattern_echoes[p_id]
        for p_id in to_drop:
            self._pattern_echoes.pop(p_id, None)

    def _determine_activity(self) -> Activity|None:
        top = (0, None)
        for p_id, echo_value in list(self._pattern_echoes.items()):
            if echo_value > top[0]:
                top = (echo_value, p_id)
        self._last_update_at = datetime.now()
        if top[0] < DEFAULT_CUTOFF or top[1] is None:
            return None
        else:
            return self._known_activities[self._pattern_activities[top[1]]]

    def _set_activity(self, activity: Activity|None):
        self._current_activity = activity
        logger.info(f"Sensor {self._name or '<Unnamed>'} set activity {activity.name if activity else '<None>'}")
        ...

    def update_state(self, force: bool = False):

        if not force:
            maxwait = 1.0 #TODO: Make period configurable?
            if self._last_update_at + timedelta(seconds=maxwait) > datetime.now():
                return self._current_activity

        self._decay()

        a = self._determine_activity()
        if a != self._current_activity:
            self._set_activity(a)


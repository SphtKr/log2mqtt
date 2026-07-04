import logging
import uuid
from src.log2mqtt.pattern import Pattern

logger = logging.getLogger(__name__)

class Activity:
    """
    An Activity is essentially a collection of Patterns plus a timeout value and a unique ID. 
    The timeout is stored as a property and is used by Clients and Users to manage their state,
    but the Activity does contain the logic to match a log entry against its Patterns.
    """

    def __init__(self, config):
        """
        Initializes the Activity with configuration.

        config: A dictionary representing an entry from the 'activities' list in the configuration.
                Example:
                {
                  'name': 'TinkerCAD',
                  'patterns': [{'userAgent': '.*tinkercad.*'}, {'url': '.*autodesk.*'}],
                  'timeout': 5
                }
        """
        self.name = config.get('name')
        self._timeout = config.get('timeout', 0)
        self._id = uuid.uuid4()
        
        # An Activity contains a list of Patterns.
        # According to the README: "multiple patterns can be specified ... and any of the 
        # specified patterns matching (with all of the pattern's arguments) in that 
        # context will satisfy the condition in that context."
        self.patterns = [Pattern(p_config) for p_config in config.get('patterns', [])]

    @property
    def timeout(self):
        """Returns the timeout value in seconds."""
        return self._timeout

    @property
    def id(self):
        """Returns the unique ID of the activity."""
        return self._id

    def matches(self, url, method, useragent) -> Pattern|None:
        """
        Returns the first pattern within this activity that matches the input.
        """
        # If there are no patterns, we assume this activity doesn't match anything.
        if not self.patterns:
            return None

        # If ANY pattern matches, the activity matches (OR logic between patterns).
        for pattern in self.patterns:
            if pattern.matches(url, method, useragent):
                return pattern

        return None

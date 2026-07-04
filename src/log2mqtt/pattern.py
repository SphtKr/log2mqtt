import logging
import re
from typing import Any
from urllib.parse import urlparse
import uuid

from log2mqtt.signal.rc import AsymmetricRCFilter

logger = logging.getLogger(__name__)

class Pattern:
    """
    Represents a rule or rules that matches a single proxy log entry.
    """

    def __init__(self, config):
        """
        Initializes the pattern with configuration.
        
        config: A dictionary representing a single pattern entry from the 
                'patterns' list in the configuration.
        """
        self._id = uuid.uuid4()

        self.url_regex = None
        self.hostname_substring = None
        self.method = None
        self.useragent_regex = None
        self.gain = 1
        self.decay = 1.0
        self.attack = 0.0001

        # The config can contain multiple keys. We check each one.
        # Based on README:
        # * url (via regex)
        # * hostname (via substring)
        # * method (exact string match)
        # * userAgent (via regex)

        if 'url' in config:
            self.url_regex = re.compile(config['url'])
        
        if 'hostname' in config:
            self.hostname_substring = config['hostname']
            
        if 'method' in config:
            self.method = config['method']
            
        if 'userAgent' in config:
            self.useragent_regex = re.compile(config['userAgent'])

        if 'gain' in config:
            self.gain = config['gain']

        if 'decay' in config:
            self.decay = config['decay']
        else:
            if 'reverb' in config: #TODO: Remove!
                self.decay = config['reverb'] # Not good but something
     
        if 'attack' in config:
            self.attack = config['attack']

    @property
    def id(self):
        """Returns the unique ID of the pattern."""
        return self._id

    def matches(self, url, method, useragent):
        """
        Returns true or false if the pattern matches the input.
        If more than one argument is specified for a single pattern, 
        then all arguments must match.
        """
        # Check method (exact match)
        if self.method is not None:
            if method is None: # Pattern requires method but no method from log
                return False
            if self.method != method:
                return False

        # Check URL regex
        if self.url_regex is not None:
            if not self.url_regex.search(url):
                return False

        # Check hostname substring
        if self.hostname_substring is not None:
            try:
                parsed_url = urlparse(url)
                hostname = parsed_url.hostname
                if hostname and self.hostname_substring not in hostname:
                    return False
            except Exception:
                pass # Presumed failure parsing URL
    
            # If URL is unparseable or parsing does not find a hostname, we fallback to checking if substring is in the raw URL
            if self.hostname_substring not in url:
                return False
            #NOTE: Do not rely on this behavior! Behavior is undefined when a URL in a Pattern is illformed or does not contain a hostname!

        # Check User-Agent regex
        if self.useragent_regex is not None:
            if useragent is None:
                return False
            if not self.useragent_regex.search(useragent):
                return False
            
        logger.debug(f"Pattern {self._id} matched ({url}, {method}, {useragent})")
        return True
        
    def filter_factory(self, state: dict[Any,Any] = {}) -> AsymmetricRCFilter:

        if 'signal_value' in state:
            signal_value = state['signal_value']
        else:
            signal_value = 0
        #FIXME: Should not support inital_value without initial_time!

        filter = AsymmetricRCFilter( self.attack, self.decay, self.gain, owner=self, initial_value=signal_value)

        return filter

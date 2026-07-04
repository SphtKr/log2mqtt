import time
import math

class AsymmetricRCFilter:
    """
    Where: Delta-T is the elapsed time since the last event (in seconds). Tau attack or Tau Delay is the target 
    time constant (in seconds). This represents the time it takes for the filter to reach roughly 63.2% of its 
    target value.
    Rule of thumb: A pulse will fully settle/decay to its final value in about Tau * r
    """
    def __init__(self, tau_attack, tau_decay, event_value, initial_value: float = 0.0, initial_time: float|None = None):
        """
        :param tau_attack: Attack time constant (seconds)
        :param tau_decay: Decay time constant (seconds)
        :param initial_value: Starting baseline value of the filter
        :param initial_time: Optional monotonic time corresponding to when the initial value was valid
        """
        self.tau_attack = tau_attack
        self.tau_decay = tau_decay
        self.event_value = event_value
        # Initial value may be provided for "warm start"--restore state from previous run--in the future.
        self.y_prev = initial_value
        self.last_time = time.monotonic() if initial_time is None else initial_time  # Tracks the timestamp of the last event

    def process_event(self, x_new, current_time=None):
        """
        Processes an event arriving at an arbitrary time.
        
        :param x_new: The value/magnitude of the new pulse event
        :param current_time: Optional monotonic time. Uses time.monotonic() if None.
        :return: The smoothed filter output at this specific moment
        """
        if current_time is None:
            current_time = time.monotonic() #TODO: Remove defaulting bahavior?

        # Handle the very first event initialization
        # if self.last_time is None:
        #     self.last_time = current_time
        #     self.y_prev = x_new
        #     return self.y_prev

        # 1. Calculate time elapsed since the last event
        dt = current_time - self.last_time
        
        # Guard against simultaneous events (dt == 0) to avoid math issues
        if dt <= 0:
            return self.y_prev

        # 2. Determine if we are attacking or decaying
        if x_new > self.y_prev:
            tau = self.tau_attack
        else:
            tau = self.tau_decay

        # 3. Compute the time-adjusted alpha
        alpha = 1.0 - math.exp(-dt / tau)

        # 4. Update filter state
        y_new = self.y_prev + alpha * (x_new - self.y_prev)

        # 5. Save state for the next event
        self.y_prev = y_new
        self.last_time = current_time

        return y_new

    @property
    def signal(self) -> float:
        # Believe this should be sufficient for "tick" decay processing...
        # the filter should handle 0-delta-T events, and a zero value passed as "new" should
        # be equivalent to a null event?
        y_new = self.process_event(0.0)
        return y_new

    def record_event(self):
        y_new = self.process_event(self.event_value)
        return y_new


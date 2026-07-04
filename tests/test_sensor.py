from src.log2mqtt.activity import Activity
from src.log2mqtt.pattern import Pattern
from src.log2mqtt.sensor import Sensor
from src.log2mqtt.activity_observer import ActivityObserver


def test_sensor_decay_uses_filter_owner_when_pattern_registry_is_absent():
    pattern = Pattern({'method': 'GET'})
    activity = Activity({'name': 'Test Activity', 'patterns': [{'method': 'GET'}]})
    sensor = Sensor('test-sensor')

    filter_instance = pattern.filter_factory()
    sensor._pattern_filters[pattern.id] = filter_instance
    sensor._pattern_activities[pattern.id] = activity.id
    sensor._known_activities[activity.id] = activity

    sensor._decay()

    assert pattern.id in sensor._pattern_filters
    assert sensor._pattern_filters[pattern.id].owner is pattern


class DummyActivityObserver(ActivityObserver):
    def __init__(self):
        self.notifications = []

    def update(self, sensor, activity, signal: float) -> None:
        self.notifications.append((sensor, activity, signal))


def test_sensor_notifies_registered_observer_on_activity_update():
    activity = Activity({'name': 'Test Activity', 'patterns': [{'method': 'GET', 'gain': 200}]})
    sensor = Sensor('test-sensor')
    observer = DummyActivityObserver()
    sensor.register_observer(observer)

    sensor.record_event(activity, activity.patterns[0])

    assert len(observer.notifications) == 1
    notified_sensor, notified_activity, notified_signal = observer.notifications[0]
    assert notified_activity is activity
    assert notified_sensor is sensor
    assert notified_signal >= 0.1

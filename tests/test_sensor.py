from src.log2mqtt.activity import Activity
from src.log2mqtt.pattern import Pattern
from src.log2mqtt.sensor import Sensor


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

import asyncio
from types import SimpleNamespace

from log2mqtt.proxy import ProxySensor


class DummyMQTTManager:
    def __init__(self):
        self.subscribe_calls = []

    async def subscribe(self, topic, callback):
        self.subscribe_calls.append((topic, callback))


def test_proxy_sensor_connects_and_subscribes_to_state_topic():
    mgr = DummyMQTTManager()
    sensor = ProxySensor(
        name="proxy-sensor",
        state_topic="log2mqtt/sensor/proxy-sensor/state",
        mqtt_manager=mgr,
    )

    asyncio.run(sensor.connect())

    assert mgr.subscribe_calls == [("log2mqtt/sensor/proxy-sensor/state", sensor._on_message)]
    assert sensor._connected


def test_proxy_sensor_updates_activity_exactly_from_state_topic():
    mgr = DummyMQTTManager()
    sensor = ProxySensor(
        name="proxy-sensor",
        state_topic="log2mqtt/sensor/proxy-sensor/state",
        mqtt_manager=mgr,
    )

    asyncio.run(sensor.connect())
    msg = SimpleNamespace(payload=b"Test Activity", topic="log2mqtt/sensor/proxy-sensor/state")
    sensor._on_message(None, None, msg)

    assert sensor.current_activity is not None
    assert sensor.current_activity.name == "Test Activity"
    assert sensor.update_state() is sensor.current_activity

    msg = SimpleNamespace(payload=b"", topic="log2mqtt/sensor/proxy-sensor/state")
    sensor._on_message(None, None, msg)
    assert sensor.current_activity is None

import asyncio
from types import SimpleNamespace

from log2mqtt.proxy import ProxySensor


class DummyMQTTClient:
    def __init__(self):
        self.connect_calls = []
        self.subscribe_calls = []
        self.on_connect = None
        self.on_message = None

    def connect_async(self, host, port, keepalive=60, **kwargs):
        self.connect_calls.append((host, port, keepalive))

    def loop_start(self):
        return None

    def subscribe(self, topic, qos=0):
        self.subscribe_calls.append((topic, qos))


def test_proxy_sensor_connects_and_subscribes_to_state_topic():
    client = DummyMQTTClient()
    sensor = ProxySensor(
        name="proxy-sensor",
        state_topic="log2mqtt/sensor/proxy-sensor/state",
        mqtt_config={"host": "localhost", "port": 1883},
        client=client,
    )

    asyncio.run(sensor.connect())

    assert client.connect_calls == [("localhost", 1883, 60)]
    assert client.on_connect is not None
    assert client.on_message is not None

    client.on_connect(client, None, None, 0)
    assert client.subscribe_calls == [("log2mqtt/sensor/proxy-sensor/state", 1)]


def test_proxy_sensor_updates_activity_exactly_from_state_topic():
    client = DummyMQTTClient()
    sensor = ProxySensor(
        name="proxy-sensor",
        state_topic="log2mqtt/sensor/proxy-sensor/state",
        mqtt_config={"host": "localhost", "port": 1883},
        client=client,
    )

    asyncio.run(sensor.connect())
    msg = SimpleNamespace(payload=b"Test Activity", topic="log2mqtt/sensor/proxy-sensor/state")
    sensor._on_message(client, None, msg)

    assert sensor.current_activity is not None
    assert sensor.current_activity.name == "Test Activity"
    assert sensor.update_state() is sensor.current_activity

    msg = SimpleNamespace(payload=b"", topic="log2mqtt/sensor/proxy-sensor/state")
    sensor._on_message(client, None, msg)
    assert sensor.current_activity is None

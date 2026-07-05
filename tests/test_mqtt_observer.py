import asyncio
import json
from pathlib import Path

from log2mqtt.activity import Activity
from log2mqtt.controller import Controller
from log2mqtt.sensor import Sensor
from log2mqtt.mqtt_observer import MQTTActivityObserver


class DummyMQTTClient:
    def __init__(self):
        self.connect_calls = []
        self.publish_calls = []
        self.tls_calls = []
        self.tls_insecure_calls = []

    def connect_async(self, host, port, keepalive=60, bind_address="", bind_port=0, clean_start=3, properties=None):
        self.connect_calls.append((host, port, keepalive))

    def publish(self, topic, payload, qos=0, retain=False, properties=None):
        self.publish_calls.append((topic, payload, qos, retain))
        return object()

    def loop_start(self):
        return None

    def loop_stop(self):
        return None

    def tls_set(self, *args, **kwargs):
        self.tls_calls.append((args, kwargs))

    def tls_insecure_set(self, value):
        self.tls_insecure_calls.append(value)


def test_mqtt_observer_publishes_discovery_and_state(tmp_path):
    sensor = Sensor("test-sensor")
    client = DummyMQTTClient()
    observer = MQTTActivityObserver(
        sensor=sensor,
        mqtt_config={"host": "localhost", "port": 1883, "discovery_prefix": "homeassistant", "base_topic": "log2mqtt"},
        client=client,
    )

    asyncio.run(observer.connect())
    activity = Activity({"name": "Test Activity", "patterns": [{"method": "GET"}]})
    observer.update(sensor, activity, 0.42)
    asyncio.run(asyncio.sleep(0))

    assert client.connect_calls == [("localhost", 1883, 60)]
    assert len(client.publish_calls) >= 2

    discovery_topic, discovery_payload, *_ = next(
        call for call in client.publish_calls if call[0].endswith("/config")
    )
    assert discovery_topic.startswith("homeassistant/sensor/")
    discovery_data = json.loads(discovery_payload)
    assert discovery_data["name"] == "test-sensor"
    assert discovery_data["unique_id"] == "log2mqtt_test-sensor"
    assert discovery_data["state_topic"] == "log2mqtt/sensor/test-sensor/state"

    state_topic, state_payload, *_ = next(
        call for call in client.publish_calls if call[0].endswith("/state")
    )
    assert state_topic == "log2mqtt/sensor/test-sensor/state"
    assert state_payload == "Test Activity"


def test_controller_registers_mqtt_senders_for_configured_sensors(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
mqtt:
  host: localhost
  port: 1883
source:
  path: /tmp/test.log
clients:
- name: hostname1
  aliases:
  - 192.168.2.110
users:
- name: usera
  usernames:
  - usera
  clients:
  - hostname1
activities: []
""".strip()
    )

    controller = Controller()
    controller.load_config(str(config_path))

    client_sensor = controller._client_sensors["hostname1"]
    user_sensor = controller._user_sensors["usera"]

    assert any(isinstance(observer, MQTTActivityObserver) for observer in client_sensor._activity_observers)
    assert any(isinstance(observer, MQTTActivityObserver) for observer in user_sensor._activity_observers)


def test_mqtt_observer_enables_insecure_tls_when_configured():
    sensor = Sensor("test-sensor")
    client = DummyMQTTClient()
    observer = MQTTActivityObserver(
        sensor=sensor,
        mqtt_config={"host": "localhost", "port": 8883, "tls_insecure": True},
        client=client,
    )

    asyncio.run(observer.connect())

    assert client.tls_calls
    assert client.tls_insecure_calls == [True]

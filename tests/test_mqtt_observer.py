import asyncio
import json

from log2mqtt.activity import Activity
from log2mqtt.controller import Controller
from log2mqtt.sensor import Sensor
from log2mqtt.mqtt_observer import MQTTActivityObserver


class DummyMQTTManager:
    def __init__(self):
        self.ensure_client_calls = []
        self.publish_calls = []

    async def _ensure_client(self):
        self.ensure_client_calls.append(True)
        return self

    def build_discovery_topic(self, object_id: str) -> str:
        return f"homeassistant/sensor/{object_id}/config"

    def build_state_topic(self, safe_name: str) -> str:
        return f"log2mqtt/sensor/{safe_name}/state"

    async def publish(self, topic: str, payload, retain: bool = False):
        self.publish_calls.append((topic, payload, retain))


def test_mqtt_observer_publishes_discovery_and_state():
    sensor = Sensor("test-sensor")
    mgr = DummyMQTTManager()
    observer = MQTTActivityObserver(sensor, mqtt_manager=mgr)

    asyncio.run(observer.connect())
    activity = Activity({"name": "Test Activity", "patterns": [{"method": "GET"}]})
    observer.update(sensor, activity, 0.42)

    assert mgr.ensure_client_calls == [True]
    assert len(mgr.publish_calls) >= 2

    discovery_topic, discovery_payload, discovery_retain = next(
        call for call in mgr.publish_calls if call[0].endswith("/config")
    )
    assert discovery_retain is True
    assert discovery_topic.startswith("homeassistant/sensor/")
    discovery_data = json.loads(discovery_payload)
    assert discovery_data["name"] == "test-sensor"
    assert discovery_data["unique_id"] == "log2mqtt_test-sensor"
    assert discovery_data["state_topic"] == f"log2mqtt/sensor/{discovery_data['unique_id']}/state"

    state_topic, state_payload, state_retain = next(
        call for call in mgr.publish_calls if call[0].endswith("/state")
    )
    assert state_retain is True
    assert state_topic == f"log2mqtt/sensor/{discovery_data['unique_id']}/state"
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
sensors:
- name: hostname1
  type: client
  publish: True
  aliases:
  - 192.168.2.110
- name: usera
  type: user
  publish: True
  usernames:
  - usera
  clients:
  - hostname1
activities: []
""".strip()
    )

    controller = Controller()
    controller.load_config(str(config_path))

    client_sensor = controller._sensors["hostname1"]
    user_sensor = controller._sensors["usera"]

    assert any(isinstance(observer, MQTTActivityObserver) for observer in client_sensor._activity_observers)
    assert any(isinstance(observer, MQTTActivityObserver) for observer in user_sensor._activity_observers)



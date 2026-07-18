import asyncio

from log2mqtt import mqtt_manager
from log2mqtt.mqtt_manager import MQTTManager


class DummyClient:
    def __init__(self, *args, **kwargs):
        self.connect_async_calls = []
        self.loop_started = False
        self.username_pw_set_calls = []
        self.tls_set_calls = []
        self.tls_insecure_calls = []
        self.publish_calls = []
        self.unsubscribe_calls = []
        self.subscribe_calls = []
        self.on_connect = None
        self.on_message = None

    def connect_async(self, host, port, keepalive=60, **kwargs):
        self.connect_async_calls.append((host, port, keepalive))

    def loop_start(self):
        self.loop_started = True

    def username_pw_set(self, username, password=None):
        self.username_pw_set_calls.append((username, password))

    def tls_set(self, *args, **kwargs):
        self.tls_set_calls.append((args, kwargs))

    def tls_insecure_set(self, value):
        self.tls_insecure_calls.append(value)

    def publish(self, topic, payload, qos=1, retain=False):
        self.publish_calls.append((topic, payload, qos, retain))

    def unsubscribe(self, topic):
        self.unsubscribe_calls.append(topic)

    def subscribe(self, topic, qos=1):
        self.subscribe_calls.append((topic, qos))


def test_build_topics_use_config_defaults_and_overrides():
    default_mgr = MQTTManager({"host": "localhost", "port": 1883})
    assert default_mgr.build_state_topic("sensor1") == "log2mqtt/sensor/sensor1/state"
    assert default_mgr.build_discovery_topic("sensor1") == "homeassistant/sensor/sensor1/config"

    custom_mgr = MQTTManager(
        {
            "host": "localhost",
            "port": 1883,
            "base_topic": "custom",
            "discovery_prefix": "customhome",
        }
    )
    assert custom_mgr.build_state_topic("sensor2") == "custom/sensor/sensor2/state"
    assert custom_mgr.build_discovery_topic("sensor2") == "customhome/sensor/sensor2/config"


def test_ensure_client_creates_client_and_applies_configuration(monkeypatch):
    monkeypatch.setattr(mqtt_manager, "Client", DummyClient)

    config = {
        "host": "localhost",
        "port": 1883,
        "username": "user",
        "password": "pass",
        "tls_insecure": True,
        "client_id": "test-client",
    }
    mgr = MQTTManager(config)

    client = asyncio.run(mgr._ensure_client())

    assert isinstance(client, DummyClient)
    assert client.connect_async_calls == [("localhost", 1883, 60)]
    assert client.loop_started is True
    assert client.username_pw_set_calls == [("user", "pass")]
    assert client.tls_set_calls, "TLS should be configured when tls_insecure is True"
    assert client.tls_insecure_calls == [True]
    assert client.on_connect.__self__ is mgr
    assert client.on_connect.__func__ is type(mgr)._on_connect
    assert client.on_message.__self__ is mgr
    assert client.on_message.__func__ is type(mgr)._on_message
    assert mgr._client is client

    # A second ensure_client call should reuse the existing client.
    client_again = asyncio.run(mgr._ensure_client())
    assert client_again is client


def test_subscribe_registers_callback_and_subscribes_on_connect(monkeypatch):
    monkeypatch.setattr(mqtt_manager, "Client", DummyClient)
    mgr = MQTTManager({"host": "localhost", "port": 1883})

    async def callback(client, userdata, msg):
        return None

    asyncio.run(mgr.subscribe("topic/1", callback))
    assert mgr._subscriptions["topic/1"] == [callback]
    assert mgr._client.subscribe_calls == []

    mgr._on_connect(mgr._client, None, None, 0)
    assert mgr._client.subscribe_calls == [("topic/1", 1)]


def test_unsubscribe_removes_callbacks_and_unsubscribes(monkeypatch):
    monkeypatch.setattr(mqtt_manager, "Client", DummyClient)
    mgr = MQTTManager({"host": "localhost", "port": 1883})

    def callback_a(client, userdata, msg):
        return None

    def callback_b(client, userdata, msg):
        return None

    asyncio.run(mgr.subscribe("topic/2", callback_a))
    asyncio.run(mgr.subscribe("topic/2", callback_b))
    assert mgr._subscriptions["topic/2"] == [callback_a, callback_b]

    asyncio.run(mgr.unsubscribe("topic/2", callback_a))
    assert mgr._subscriptions["topic/2"] == [callback_b]
    assert mgr._client.unsubscribe_calls == []

    asyncio.run(mgr.unsubscribe("topic/2"))
    assert "topic/2" not in mgr._subscriptions
    assert mgr._client.unsubscribe_calls == ["topic/2"]


def test_publish_uses_client_publish(monkeypatch):
    monkeypatch.setattr(mqtt_manager, "Client", DummyClient)
    mgr = MQTTManager({"host": "localhost", "port": 1883})
    client = asyncio.run(mgr._ensure_client())

    async def sync_to_thread(fn, *args, **kwargs):
        return fn(*args, **kwargs)

    monkeypatch.setattr(asyncio, "to_thread", sync_to_thread)
    asyncio.run(mgr.publish("topic/3", "payload", retain=True))

    assert client.publish_calls == [("topic/3", "payload", 1, True)]

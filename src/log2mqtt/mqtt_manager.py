import asyncio
import logging
import ssl
from typing import Any, Callable, Dict, Tuple

from paho.mqtt.client import CallbackAPIVersion, Client
import warnings

logger = logging.getLogger(__name__)


class MQTTManager:
    """Manager representing a single broker connection.

    Use MQTTManager.get_default() to obtain a default manager, or
    MQTTManager.get_manager(name, mqtt_config) to create/get a named manager.
    """

    _instances: Dict[str, "MQTTManager"] = {}

    @classmethod
    def get_manager(
        cls, name: str, mqtt_config: dict[str, Any] | None = None
    ) -> "MQTTManager":

        if name in cls._instances:
            return cls._instances[name]
        if mqtt_config is None:
            raise ValueError("mqtt_config required when creating a new MQTTManager")
        mgr = MQTTManager(mqtt_config)
        cls._instances[name] = mgr
        return mgr

    @classmethod
    def get_default(cls, mqtt_config: dict[str, Any] | None = None) -> "MQTTManager":

        if "default" in cls._instances:
            return cls._instances["default"]
        if mqtt_config is None:
            raise ValueError("No default MQTTManager exists; provide mqtt_config to create one")
        return cls.get_manager("default", mqtt_config)

    def __init__(self, mqtt_config: dict[str, Any]) -> None:
        self._mqtt_config = mqtt_config or {}
        self._client: Client | None = None
        self._subscriptions: Dict[str, list[Callable[[Any, Any, Any], None]]] = {}
        self._connected = False
        self._connecting = False
        self._lock = asyncio.Lock()

    async def _ensure_client(self) -> Client:
        async with self._lock:
            if self._client is not None:
                return self._client

            # avoid concurrent/duplicate connect attempts
            self._connecting = True

            config = self._mqtt_config
            host = config.get("host")
            if not host:
                raise ValueError("MQTT host is required for this manager")

            client_id = config.get("client_id")
            client = Client(callback_api_version=CallbackAPIVersion.VERSION2, client_id=client_id)

            username = config.get("username")
            password = config.get("password")
            if username is not None:
                client.username_pw_set(username, password)

            if config.get("tls_insecure", False):
                client.tls_set(cert_reqs=ssl.CERT_NONE)
                client.tls_insecure_set(True)

            client.on_connect = self._on_connect
            client.on_message = self._on_message

            await asyncio.to_thread(client.connect_async, host, int(config.get("port", 1883)), keepalive=int(config.get("keepalive", 60)))
            client.loop_start()
            self._client = client
            return client

    def _on_connect(self, client: Client, userdata: Any, flags: Any, rc: int, properties: Any = None) -> None:
        logger.info("MQTTManager connected to %s", self._mqtt_config.get("host"))
        # mark connected and subscribe to all registered topics
        self._connected = True
        self._connecting = False
        for topic in list(self._subscriptions.keys()):
            try:
                client.subscribe(topic, qos=1)
            except Exception:
                logger.exception("Failed to subscribe to %s on connect", topic)

    def _on_message(self, client: Client, userdata: Any, msg: Any) -> None:
        callbacks = self._subscriptions.get(msg.topic, [])
        for cb in list(callbacks):
            try:
                cb(client, userdata, msg)
            except Exception:
                logger.exception("Callback for topic %s failed", msg.topic)

    async def subscribe(self, topic: str, callback: Callable[[Any, Any, Any], None]) -> None:
        client = await self._ensure_client()
        # Register callback; actual broker subscription happens in _on_connect
        self._subscriptions.setdefault(topic, []).append(callback)

    async def unsubscribe(self, topic: str, callback: Callable[[Any, Any, Any], None] | None = None) -> None:
        if self._client is None:
            return
        if callback is None:
            self._subscriptions.pop(topic, None)
            await asyncio.to_thread(self._client.unsubscribe, topic)
            return
        lst = self._subscriptions.get(topic, [])
        if callback in lst:
            lst.remove(callback)
        if not lst:
            self._subscriptions.pop(topic, None)
            await asyncio.to_thread(self._client.unsubscribe, topic)

    async def publish(self, topic: str, payload: Any, retain: bool = False) -> None:
        client = await self._ensure_client()
        await asyncio.to_thread(client.publish, topic, payload, qos=1, retain=retain)

    def build_state_topic(self, safe_name: str) -> str:
        base_topic = self._mqtt_config.get("base_topic", "log2mqtt")
        return f"{base_topic}/sensor/{safe_name}/state"

    def build_discovery_topic(self, object_id: str) -> str:
        discovery_prefix = self._mqtt_config.get("discovery_prefix", "homeassistant")
        return f"{discovery_prefix}/sensor/{object_id}/config"

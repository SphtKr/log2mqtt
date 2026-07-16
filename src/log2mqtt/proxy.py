import asyncio
import logging
import ssl
from typing import Any

from paho.mqtt.client import CallbackAPIVersion, Client

from log2mqtt.activity import Activity
from log2mqtt.sensor import Sensor

logger = logging.getLogger(__name__)


class ProxySensor(Sensor):
    def __init__(
        self,
        name: str | None = None,
        subject_type: str | None = None,
        state_topic: str | None = None,
        mqtt_config: dict[str, Any] | None = None,
        client: Any | None = None,
    ) -> None:
        super().__init__(name, subject_type)
        if not state_topic:
            raise ValueError("state_topic is required for ProxySensor")

        self._state_topic = state_topic
        self._mqtt_config = mqtt_config or {}
        self._client = client
        self._connected = False
        self._activity_by_name: dict[str, Activity] = {}

    async def connect(self) -> None:
        if self._connected:
            return

        host = self._mqtt_config.get("host")
        if not host:
            raise ValueError("MQTT host is required")

        client = self._client
        if client is None:
            client = Client(
                callback_api_version=CallbackAPIVersion.VERSION2,
                client_id=self._mqtt_config.get("client_id", self.name or "proxy-sensor"),
            )
            self._client = client

        client.on_connect = self._on_connect
        client.on_message = self._on_message

        username = self._mqtt_config.get("username")
        password = self._mqtt_config.get("password")
        if username is not None:
            client.username_pw_set(username, password)

        if self._mqtt_config.get("tls_insecure", False):
            client.tls_set(cert_reqs=ssl.CERT_NONE)
            client.tls_insecure_set(True)

        await asyncio.to_thread(
            client.connect_async,
            host,
            int(self._mqtt_config.get("port", 1883)),
            keepalive=int(self._mqtt_config.get("keepalive", 60)),
        )
        client.loop_start()
        self._connected = True

    def _on_connect(self, client: Any, userdata: Any, flags: Any, rc: int, properties: Any = None) -> None:
        logger.info(f"ProxySensor subscribing to MQTT topic {self._state_topic}")
        client.subscribe(self._state_topic, qos=1)

    def _on_message(self, client: Any, userdata: Any, msg: Any) -> None:
        payload = None
        try:
            payload = msg.payload.decode("utf-8")
        except Exception:
            logger.warning("Received non-decodable MQTT payload for ProxySensor", exc_info=True)

        activity = self._activity_from_payload(payload)
        if activity != self._current_activity:
            signal = 1.0 if activity else 0.0
            self._set_activity(activity, signal)

    def _activity_from_payload(self, payload: str | None) -> Activity | None:
        if payload is None:
            return None

        value = payload.strip()
        if not value:
            return None

        if value in self._activity_by_name:
            return self._activity_by_name[value]

        activity = Activity({"name": value, "patterns": []})
        self._activity_by_name[value] = activity
        return activity

    def update_state(self, force: bool = False):
        return self._current_activity

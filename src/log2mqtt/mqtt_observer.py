import asyncio
import json
import logging
import re
import ssl
from typing import Any

from paho.mqtt.client import CallbackAPIVersion, Client

from log2mqtt.activity import Activity
from log2mqtt.activity_observer import ActivityObserver
from log2mqtt.sensor import Sensor

logger = logging.getLogger(__name__)


class MQTTActivityObserver(ActivityObserver):
    def __init__(self, sensor: Sensor, mqtt_config: dict[str, Any], client: Any | None = None) -> None:
        self._sensor = sensor
        self._mqtt_config = mqtt_config or {}
        self._client = client
        self._connected = False
        self._sensor_name = sensor.name or "unnamed"
        self._safe_name = self._sanitize_identifier(self._sensor_name)
        self._unique_id = f"log2mqtt{'' if sensor.subject_type is None else f'_{sensor.subject_type}'}_{self._safe_name}"
        self._object_id = self._unique_id # per docs best practice
        self._default_entity_id = f"sensor.{self._unique_id}"
        self._discovery_topic = self._build_discovery_topic()
        self._state_topic = self._build_state_topic()

    @staticmethod
    def _sanitize_identifier(value: str) -> str:
        cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "-", value or "sensor")
        return cleaned.strip("-").lower()

    def _build_discovery_topic(self) -> str:
        discovery_prefix = self._mqtt_config.get("discovery_prefix", "homeassistant")
        return f"{discovery_prefix}/sensor/{self._object_id}/config"

    def _build_state_topic(self) -> str:
        base_topic = self._mqtt_config.get("base_topic", "log2mqtt")
        return f"{base_topic}/sensor/{self._object_id}/state"

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
                client_id=self._unique_id,
            )
            self._client = client

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
        await self._publish_discovery()

    async def _publish_discovery(self) -> None:
        payload = {
            "name": self._sensor_name,
            "unique_id": self._unique_id,
            "default_entity_id": self._default_entity_id,
            "state_topic": self._state_topic,
            "icon": "mdi:clipboard-pulse",
            "force_update": True,
        }
        await self._publish(self._discovery_topic, json.dumps(payload), retain=True)

    async def _publish_state(self, activity: Activity | None) -> None:
        value = activity.name if activity else None
        await self._publish(self._state_topic, value, retain=True)

    async def _publish(self, topic: str, payload: Any, retain: bool = False) -> None:
        if self._client is None:
            raise RuntimeError("MQTT client is not configured")
        await asyncio.to_thread(self._client.publish, topic, payload, qos=1, retain=retain)

    def update(self, sensor: Sensor, activity: Activity | None, signal: float) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(self._publish_state(activity))
            return

        loop.create_task(self._publish_activity(activity))

    async def _publish_activity(self, activity: Activity | None) -> None:
        if not self._connected:
            await self.connect()
        await self._publish_state(activity)

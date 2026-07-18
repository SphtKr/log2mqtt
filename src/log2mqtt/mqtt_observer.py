import asyncio
import json
import logging
import re
import ssl
from typing import Any

from log2mqtt.mqtt_manager import MQTTManager

from log2mqtt.activity import Activity
from log2mqtt.activity_observer import ActivityObserver
from log2mqtt.sensor import Sensor

logger = logging.getLogger(__name__)


class MQTTActivityObserver(ActivityObserver):
    def __init__(self, sensor: Sensor, mqtt_manager: "MQTTManager" | None = None) -> None:
        self._sensor = sensor
        # Prefer explicit manager; otherwise expect a default manager to exist
        if mqtt_manager is not None:
            self._manager = mqtt_manager
        else:
            from log2mqtt.mqtt_manager import MQTTManager

            self._manager = MQTTManager.get_default()

        self._connected = False
        self._sensor_name = sensor.name or "unnamed"
        self._safe_name = self._sanitize_identifier(self._sensor_name)
        self._unique_id = f"log2mqtt{'' if sensor.subject_type is None else f'_{sensor.subject_type}'}_{self._safe_name}"
        self._object_id = self._unique_id  # per docs best practice
        self._default_entity_id = f"sensor.{self._unique_id}"
        self._discovery_topic = self._manager.build_discovery_topic(self._object_id)
        self._state_topic = self._manager.build_state_topic(self._object_id)

    @staticmethod
    def _sanitize_identifier(value: str) -> str:
        cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "-", value or "sensor")
        return cleaned.strip("-").lower()

    # topic builders removed; manager provides topic creation

    async def connect(self) -> None:
        if self._connected:
            return

        # Ensure manager's client exists/connected and publish discovery
        await self._manager._ensure_client()
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
        await self._manager.publish(topic, payload, retain=retain)

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

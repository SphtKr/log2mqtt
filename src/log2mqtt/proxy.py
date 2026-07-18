import asyncio
import logging
import ssl
from typing import Any

from paho.mqtt.client import CallbackAPIVersion, Client

from log2mqtt.activity import Activity
from log2mqtt.sensor import Sensor
from log2mqtt.mqtt_manager import MQTTManager

logger = logging.getLogger(__name__)


class ProxySensor(Sensor):
    def __init__(
        self,
        name: str | None = None,
        subject_type: str | None = None,
        state_topic: str | None = None,
        mqtt_manager: "MQTTManager" | None = None,
    ) -> None:
        super().__init__(name, subject_type)
        if not state_topic:
            raise ValueError("state_topic is required for ProxySensor")

        self._state_topic = state_topic
        # Prefer explicit manager; otherwise expect a default manager to exist
        if mqtt_manager is not None:
            self._manager = mqtt_manager
        else:
            self._manager = MQTTManager.get_default()
        self._connected = False
        self._activity_by_name: dict[str, Activity] = {}

    async def connect(self) -> None:
        if self._connected:
            return

        # subscribe using manager (manager ensures client exists)
        await self._manager.subscribe(self._state_topic, self._on_message)
        self._connected = True


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

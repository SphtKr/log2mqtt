
import asyncio
from datetime import datetime, timedelta
import logging
from typing import Dict

import yaml
from log2mqtt.activity import Activity
from log2mqtt.logprocessor import LogProcessor
from log2mqtt.sensor import Sensor
from log2mqtt.mqtt_observer import MQTTActivityObserver

logger = logging.getLogger(__name__)

class Controller:
    def __init__(self) -> None:
        self._config = {}  # Initialize an empty dict to store the config
        self._ignore_activity = None
        self._activities = []
        self._sensors = []
        self._client_sensors: Dict[str,Sensor] = {}
        self._user_sensors: Dict[str,Sensor] = {}
        self._user_clients: Dict[str,Sensor] = {}
        self._mqtt_senders = []
        ...

    def load_config(self, config_path: str):
        with open(config_path, 'r') as f:
            self._config = yaml.safe_load(f)  # Load the YAML file and store it in _config

        self._activities = []
        self._client_sensors = {}
        self._user_sensors = {}
        self._user_clients = {}
        self._mqtt_senders = []

        if 'ignore' in self._config:
            self._ignore_activity = Activity({"name":"ignore", "patterns": self._config['ignore']})

        for activity_config in self._config.get('activities', []):
            self._activities.append(Activity(activity_config))

        mqtt_config = self._config.get('mqtt', {}) or {}

        for client_config in self._config.get('clients', []):
            sensor = Sensor(client_config.get('name', None), 'client')
            if 'name' in client_config:
                self._client_sensors[client_config.get('name')] = sensor
            for alias in client_config.get('aliases', []):
                self._client_sensors[alias] = sensor
            if mqtt_config.get('host') and client_config.get("publish", False):
                sender = MQTTActivityObserver(sensor, mqtt_config)
                sensor.register_observer(sender)
                self._mqtt_senders.append(sender)
            #TOOO: Handle `sensor` bool in config
        logger.debug(f"{self._client_sensors=}")

        for user_config in self._config.get('users', []):
            sensor = Sensor(user_config.get('name', None), 'user')
            if 'name' in user_config:
                self._user_sensors[user_config.get('name')] = sensor
            for username in user_config.get('usernames',  []):
                self._user_sensors[username]  = sensor
            for client in user_config.get('clients',[]):
                self._user_clients[client] = sensor
            if mqtt_config.get('host') and user_config.get("publish", False):
                sender = MQTTActivityObserver(sensor, mqtt_config)
                sensor.register_observer(sender)
                self._mqtt_senders.append(sender)
        logger.debug(f"{self._user_sensors=}")
            
    async def start(self):
        for sender in self._mqtt_senders:
            await sender.connect()

        self._logparser = LogProcessor(self._config['source'], self._log_callback)
        self._update_task = asyncio.create_task(self._update_timer())
        try:
            await self._logparser.start()
        except asyncio.CancelledError:
            self._update_task.cancel()

    async def _update_timer(self):
        while True:
            logger.debug('_update_timer called')
            maxwait = 1.0 #TODO: Make period configurable?
            try:
                await asyncio.sleep(maxwait)
                sensors = { sensor for sensor in list(self._client_sensors.values()) + list(self._user_sensors.values()) }
                for sensor in sensors:
                    logger.debug(f"Updating sensor {sensor.name}")
                    sensor.update_state()
            except asyncio.CancelledError:
                logger.debug("Exiting update timer task")
                break

            
    def _log_callback(self, user, client, url, method, user_agent):
        if self._ignore_activity and self._ignore_activity.matches(url, method, user_agent):
            return
        
        pattern = None
        activity = None
        for activity in self._activities:
            pattern = activity.matches(url, method, user_agent)
            if pattern:
                break
        else:
            activity = None
            pattern = None
            return
            
        user_sensor = self._user_sensors.get(user, None) if user else self._user_clients.get(client,None)

        client_sensor = self._client_sensors.get(client, None)
        logger.debug(f"Got user_sensor {user_sensor.name if user_sensor else '-'} and client_sensor {client_sensor.name if client_sensor else '-'}")
        if client_sensor:
            logger.debug(f"Sending event to {client_sensor.name}")
            client_sensor.record_event(activity, pattern)

        if user_sensor:
            logger.debug(f"Sending event to {user_sensor.name}")
            user_sensor.record_event(activity, pattern)
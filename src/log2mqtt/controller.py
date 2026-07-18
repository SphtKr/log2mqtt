
import asyncio
from datetime import datetime, timedelta
import logging
from typing import Dict

import yaml
from log2mqtt.aggregate import AggregateSensor
from log2mqtt.activity import Activity
from log2mqtt.logprocessor import LogProcessor
from log2mqtt.sensor import Sensor
from log2mqtt.mqtt_observer import MQTTActivityObserver
from log2mqtt.proxy import ProxySensor
from log2mqtt.mqtt_manager import MQTTManager

logger = logging.getLogger(__name__)

class Controller:
    def __init__(self) -> None:
        self._config = {}  # Initialize an empty dict to store the config
        self._ignore_activity = None
        self._activities = []
        self._sensors = {}
        self._mqtt_connectors = []
        ...

    def load_config(self, config_path: str):
        try:
            with open(config_path, 'r') as f:
                self._config = yaml.safe_load(f)

        except FileNotFoundError:
            raise Exception(f"The file {config_path} was not found.")
        except yaml.YAMLError as e:
            raise Exception(f"There was an error parsing the YAML file {config_path}: {str(e)}")
        except Exception as e:
            raise Exception(f"An unexpected error occurred while loading the config file {config_path}: {str(e)}")
    
        self._activities = []
        self._sensors = {}
        self._mqtt_connectors = []

        if 'ignore' in self._config:
            self._ignore_activity = Activity({"name":"ignore", "patterns": self._config['ignore']})

        for activity_config in self._config.get('activities', []):
            self._activities.append(Activity(activity_config))

        mqtt_config = self._config.get('mqtt', {}) or {}

        # If MQTT is configured, create a default manager for the broker
        mqtt_manager = None
        if mqtt_config.get('host'):
            mqtt_manager = MQTTManager.get_default(mqtt_config)

        for sensor_config in self._config.get('sensors', []):
            name = sensor_config.get('name','sensor')
            #TODO: Skip duplicate names
            if sensor_config.get('type' == 'aggregate') or sensor_config.get('components',False):
                if sensor_config.get('type','') != 'aggregate':
                    logger.warning(f"Non-aggregate sensor {name} has components, skipping!")
                    continue
                if len(sensor_config.get('components',[])) <= 0:
                    logger.warning(f"No components for aggregate sensor {name}, skipping.")
                    continue
                strategy = sensor_config.get('strategy','latest')
                if strategy not in ['priority','latest']:
                    logger.warning(f"Unknown strategy \"{strategy}\" specified, using \"latest\" instead!")
                    strategy = 'latest'
                sensor = AggregateSensor(name, "aggregate", strategy)
                pri_list = []
                for component_config in sensor_config.get('components', []):
                    comp_name = component_config.get('name')
                    if comp_name in self._sensors:
                        comp_sensor = self._sensors[comp_name]
                        pri_list.append(comp_sensor)
                        comp_sensor.register_observer(sensor)
                    else:
                        logger.warning(f"Unknown sensor name {comp_name} listed as component, ignoring!")
                if strategy == 'priority':
                    sensor.set_priority(pri_list)
                if strategy == 'latest':
                    pass
            elif sensor_config.get('type' == 'proxy') or sensor_config.get('topic',False):
                if sensor_config.get('type','') != 'proxy':
                    logger.warning(f"Non-proxy sensor {name} has topic, skipping!")
                    continue
                if len(sensor_config.get('topic',[])) <= 0:
                    logger.warning(f"No topic for proxy sensor {name}, skipping.")
                    continue
                topic = sensor_config.get('topic')
                sensor = ProxySensor(name, "proxy", topic, mqtt_manager=mqtt_manager)
                self._mqtt_connectors.append(sensor)
            else:
                sensor = Sensor(name, sensor_config.get('type', 'sensor'))
            self._sensors[name] = sensor
            for alias in sensor_config.get('aliases', []):
                self._sensors[alias] = sensor
            if mqtt_config.get('host') and sensor_config.get("publish", False):
                sender = MQTTActivityObserver(sensor, mqtt_manager=mqtt_manager)
                sensor.register_observer(sender)
                self._mqtt_connectors.append(sender)

        logger.debug(f"{self._sensors=}")


    async def start(self):
        try:
            with open(self._config['source']['path'], 'r'):
                pass
        except KeyError:
            raise Exception(f"Source path not defined at source.path in config; verify configuration.")
        except FileNotFoundError:
            raise Exception(f"The file {self._config['source']['path']} was not found.")
        except IOError:
            raise Exception(f"An error occurred while reading the file {self._config['source']}.")

        for connector in self._mqtt_connectors:
            await connector.connect()

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
                sensors = { sensor for sensor in list(self._sensors.values()) }
                for sensor in sensors:
                    logger.debug(f"Updating sensor {sensor.name}")
                    sensor.update_state()
            except asyncio.CancelledError:
                logger.debug("Exiting update timer task")
                break

            
    def _log_callback(self, user, client, url, method, user_agent):
        if self._ignore_activity and self._ignore_activity.matches(url, method, user_agent):
            return
        
        user_sensor = self._sensors.get(user, None)
        client_sensor = self._sensors.get(client, None)
        logger.debug(f"Got user_sensor {user_sensor.name if user_sensor else '-'} and client_sensor {client_sensor.name if client_sensor else '-'}")
        sensors = [s for s in [user_sensor, client_sensor] if s]
        if len(sensors) <= 0: return

        pattern = None
        activity = None
        for activity in self._activities:
            pattern = activity.matches(url, method, user_agent)
            if pattern:
                if pattern.initiate:
                    allowed_sensors = sensors
                else:
                    allowed_sensors = [s for s in sensors if s and s.current_activity == activity]
                    logger.debug(f"Sustaining Activity {activity.name} on sensors {', '.join([s.name for s in allowed_sensors])}")
                if len(allowed_sensors) > 0:
                    for sensor in allowed_sensors:
                        logger.debug(f"Sending event to {sensor.name}")
                        sensor.record_event(activity, pattern)
                    break
        else:
            activity = None
            pattern = None
            return

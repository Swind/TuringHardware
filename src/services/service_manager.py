#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
from logzero import logger
from services.output_temp_service import OutputTempService
from services.tank_temp_service import TankTempService
from services.tank_water_service import TankWaterService
from services.refill_service import RefillService
from services.heater import Heater
from services.barista.barista import Barista, WasteWaterPosition


class ServiceManager(object):
    """ Service manager
    """

    def __init__(self):
        self._services = {}

    def import_config(self, configs, hwmanager, busmanager):
        """
        Args:
            configs (dict): service configuration
            hwmanager (HardwareManager): get hardware from hwmanager
            busmanager (BusManager): create the client to connect each services
        """
        for config in configs:
            service_name = list(config.keys())[0]
            if service_name not in SERVICE_MAPPING:
                logger.error("Cannot resolve '%s' service", service_name)
                continue

            if 'enable' not in config[service_name]:
                logger.warning(
                    "Cannot find enable field in '%s', default is disabled",
                    service_name)
                continue

            if config[service_name]['enable'] is not True:
                logger.info("Service '%s' is disabled'", service_name)
                continue

            # Use the busmanager to create a bus client for this service
            bus_path = config[service_name]['path']
            bus = busmanager.create_bus_client(bus_path)
            bus.start()

            service = SERVICE_MAPPING[service_name](config[service_name],
                                                    hwmanager, bus)
            if service is not None:
                logger.info("Create service instance '%s'", service_name)
                self._services[service_name] = service
            else:
                logger.error("Cannot create service instance '%s'",
                             service_name)
        return True

    def find_service(self, name):
        if name not in self._services:
            return None
        return self._services[name]

    def start_all_services(self):
        loop = asyncio.get_event_loop()
        for _, service in self._services.items():
            loop.create_task(service.start())

    async def stop_all_services(self):
        for _, service in self._services.items():
            await service.stop()


def create_output_temp_service(service_config, hwmanager, bus):
    """
    Args:
        service_config(dict): output temperautre service configuration
    """
    scan_interval_ms = service_config['scan_interval_ms']
    dev = service_config['dev']
    hardware = hwmanager.find_hardware(dev)
    if hardware is None:
        logger.error("Cannot get dev '%s' for output temp service", dev)
        return None
    return OutputTempService(hardware, scan_interval_ms, bus)


def create_tank_temp_service(service_config, hwmanager, bus):
    """
    Args:
        service_config(dict): tank temperature service configuration
    """
    scan_interval_ms = service_config['scan_interval_ms']
    dev = service_config['dev']
    hardware = hwmanager.find_hardware(dev)
    if hardware is None:
        logger.error("Cannot get dev '%s' in tank temp service", dev)
        return None
    return TankTempService(hardware, scan_interval_ms, bus)


def create_tank_water_service(service_config, hwmanager, bus):
    """
    Args:
        service_config(dict): tank water service configuration
    """
    scan_interval_ms = service_config['scan_interval_ms']
    dev = service_config['dev']
    hardware = hwmanager.find_hardware(dev)
    if hardware is None:
        logger.error("Cannot get dev '%s' in tank water service", dev)
        return None
    return TankWaterService(hardware, scan_interval_ms, bus)


def create_refill_service(service_config, hwmanager, bus):
    """
    Args:
        service_config(dict): refill service configuration
    """
    dev = service_config['dev']
    scan_interval_ms = service_config['scan_interavl_ms']
    hardware = hwmanager.find_hardware(dev)
    if hardware is None:
        logger.error("Cannot get dev '%s' in refill service", dev)
        return None
    return RefillService(hardware, scan_interval_ms, bus)


def create_heater_service(service_config, hwmanager, bus):
    """
    Args:
        service_config(dict): heater service configuration
    """
    scan_interval_ms = service_config['scan_interval_ms']
    pwm = service_config['pwm_dev']
    pid = service_config['pid_dev']
    pwm_dev = hwmanager.find_hardware(pwm)
    pid_dev = hwmanager.find_hardware(pid)
    if pwm_dev is None:
        logger.error("Cannot get dev '%s' in heater service", pwm)
        return None
    if pid_dev is None:
        logger.error("Cannot get dev '%s' in heater service", pid)
        return None
    return Heater(pwm_dev, pid_dev, scan_interval_ms, bus)


def create_barista_service(service_config, hwmanager, bus):
    """
    Args:
        service_config(dict): heater service configuration
    """
    moving = service_config['moving_dev']
    extruder = service_config['extruder_dev']
    pid = service_config['pid_dev']
    moving_dev = hwmanager.find_hardware(moving)
    extruder_dev = hwmanager.find_hardware(extruder)
    pid_dev = hwmanager.find_hardware(pid)
    if moving_dev is None:
        logger.error("Cannot get dev '%s' in barista service", moving_dev)
        return None
    if extruder_dev is None:
        logger.error("Cannot get dev '%s' in barista service", extruder_dev)
        return None
    if pid_dev is None:
        logger.error("Cannot get dev '%s' in barista service", pid_dev)
        return None
    pos = service_config['waste_water_position']
    speed = service_config['default_moving_speed']
    return Barista(moving_dev, extruder_dev, pid_dev,
                   WasteWaterPosition(x=pos['x'], y=pos['y'], z=pos['z']),
                   speed, bus)


SERVICE_MAPPING = {
    "output_temp_service": create_output_temp_service,
    "tank_temp_service": create_tank_temp_service,
    "tank_water_service": create_tank_water_service,
    "refill_service": create_refill_service,
    "heater": create_heater_service,
    "barista": create_barista_service
}

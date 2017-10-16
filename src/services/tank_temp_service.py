#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from concurrent import futures
import asyncio
from logzero import logger
from hardware.error import HardwareError


class TankTempService(object):
    def __init__(self, sensor, scan_interval_ms, bus):
        """
        Args:
            sensor: temperature sensor, can be max31856 and max31865
            scan_interval_ms (int): scan interval in milisecond
        """
        self._sensor = sensor
        self._interval = scan_interval_ms
        self._error_count = 0
        self._bus = bus

        self._tempc = None
        self._tempc_available = False
        self._message = 'Not ready'
        self._stop = False
        self._stop_event = asyncio.Event()

    async def pub_tank_temperature(self):
        if not self._sensor.is_connected() and not self._sensor.connect():
            self._message = 'Cannot connect to sensor'
            await self._bus.pub('tank.temperature', self._get_status())
            return

        try:
            tempc = self._sensor.read_measure_temp_c()
            self._tempc = tempc
            self._tempc_available = True
            await self._bus.pub('tank.temperature', self._get_status())
        except HardwareError as error:
            self._tempc_available = False
            self._error_count += 1
            self._sensor.disconnect()
            self._message = "output sensor '%s' got error: '%s'" % (
                error.name, error.message)
            await self._bus.pub('tank.temperature', self._get_status())

    async def start(self):
        await self._bus.reg_rep('tank_temperature', self.command_callback)
        self._stop = False
        while not self._stop:
            await self.pub_tank_temperature()
            await asyncio.sleep(float(self._interval) / 1000)
        self._stop_event.set()

    async def stop(self):
        self._stop = True
        await self._stop_event.wait()

    async def command_callback(self, data):
        if data['command'] == 'get':
            return self._get_status()

    def _get_status(self):
        if self._tempc_available is True:
            return {'status': 'ok', 'temperature': self._tempc}
        return {'status': 'error', 'message': self._message}


class TankTempClient(object):
    def __init__(self, bus):
        self._bus = bus

    async def get_temperature(self):
        try:
            response = await self._bus.req('tank.temperature',
                                           {'command': 'get'})
            if response['status'] != 'ok':
                logger.error("Cannot get tank temperature")
                return None
            return response['temperature']
        except futures.TimeoutError:
            logger.error("Request get 'tank.temperature' timeout")
            return None

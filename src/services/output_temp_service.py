#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from concurrent import futures
import asyncio
from logzero import logger
from hardware.error import HardwareError


class OutputTempService(object):
    def __init__(self, sensor, scan_interval_ms, bus):
        """
        Args:
            sensor: temperature sensor, can be max31856 and max31865
            scan_interval_ms (int): scan interval in milisecond
        """
        self._sensor = sensor
        self._bus = bus
        self._interval = scan_interval_ms
        self._error_count = 0
        self._tempc = None
        self._stop = False
        self._stop_event = asyncio.Event()
        self._temp_available = False
        self._message = "Not ready"

    async def pub_output_water_temperature(self):
        if not self._sensor.is_connected() and not self._sensor.connect():
            self._temp_available = False
            self._message = "Cannot connect to sensor"
            await self._bus.pub('output.temperature', self._status())

        try:
            tempc = self._sensor.read_measure_temp_c()
            self._tempc = tempc
            self._message = None
            self._temp_available = True
            await self._bus.pub('output.temperature', self._status())
        except HardwareError as error:
            self._temp_available = False
            self._error_count += 1
            self._message = "output sensor '%s' got error: '%s'" % (
                error.name, error.message)
            self._sensor.disconnect()
            await self._bus.pub('output.temperature', self._status())

    async def start(self):
        self._stop = False
        while not self._stop:
            await self.pub_output_water_temperature()
            await asyncio.sleep(float(self._interval) / 1000)
        self._stop_event.set()

    async def stop(self):
        self._stop = True
        await self._stop_event.wait()

    async def command_callback(self, data):
        cmd = data['command']
        if cmd == 'get':
            return self._status()

    def _status(self):
        if self._temp_available is True:
            return {
                "status": "ok",
                "temperature": self._tempc,
                "error_count": self._error_count
            }
        else:
            return {"status": "error", "message": self._message}


class OutputTempClient(object):
    def __init__(self, bus):
        self._bus = bus

    async def get_temperature(self):
        try:
            response = await self._bus.req('output.temperature',
                                           {'command': 'get'})
            if response['status'] != 'ok':
                logger.warn("Cannot get output temperature: %s",
                            response['message'])
                return None
            return response['temperature']
        except futures.TimeoutError:
            logger.warn("Cannot get output temperature: request timeout")
            return None

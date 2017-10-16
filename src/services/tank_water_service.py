#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from concurrent import futures
import asyncio
from logzero import logger


class TankWaterService(object):
    def __init__(self, sensor, scan_interval_ms, bus):
        """
        Args:
            sensor (water detector):
            scan_interval_ms (int): scan interval in milisecond
        """
        self._sensor = sensor
        self._interval = scan_interval_ms
        self._bus = bus

        self._available = False
        self._message = 'Not ready'
        self._is_water_full = None
        self._stop = False
        self._stop_event = asyncio.Event()

    async def start(self):
        await self._bus.reg_rep('tank.water', self.rep_water_command)
        self._stop = False
        while not self._stop:
            await self.pub_water_status()
            await asyncio.sleep(float(self._interval) / 1000)
        self._stop_event.set()

    async def stop(self):
        self._stop = True
        await self._stop_event.wait()

    async def pub_water_status(self):
        if not self._sensor.is_connected() and not self._sensor.connect():
            self._available = False
            self._message = 'Cannot connect to water detector'
            await self._bus.pub('tank.water', self._get_status())
            return

        is_water_full = self._sensor.is_water_full()
        self._available = True
        if self._is_water_full != is_water_full:
            self._is_water_full = is_water_full
            await self._bus.pub('tank.water', self._get_status())

    async def rep_water_command(self, data):
        cmd = data['command']
        if cmd == 'get':
            return self._get_status()
        return {"status": "error", "message": "Unknown command '%s'" % cmd}

    def _get_status(self):
        if self._available is True:
            return {"status": "ok", "water": self._is_water_full}
        return {'status': "error", 'message': self._message}


class TankWaterClient(object):
    def __init__(self, bus):
        self._bus = bus

    async def get_water_level(self):
        try:
            response = await self._bus.req('tank.water', {'command': 'get'})
            if response['status'] != 'ok':
                logger.warn("Cannot get 'tank.water' status: %s",
                            response['message'])
                return None
            return response['water']
        except futures.TimeoutError:
            logger.warn("Cannot get 'tank.water' status: request timeout")
            return None

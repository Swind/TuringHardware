#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from concurrent import futures
import asyncio
from logzero import logger
from services.tank_water_service import TankWaterClient


class RefillService(object):
    def __init__(self, pwm, scan_interval_ms, bus):
        super(RefillService, self).__init__()
        self._pwm = pwm
        self._pwm_task = None
        self._bus = bus
        self._pause = False
        self._interval_ms = scan_interval_ms
        self._stop = False
        self._stop_event = asyncio.Event()
        self._tank_water_client = TankWaterClient(bus)

    async def start(self):
        await self._bus.reg_rep('tank.refill', self.command_callback)
        self._stop = False
        while not self._stop:
            if self._pause is False:
                water_level = await self._tank_water_client.get_water_level()
                if water_level is None or water_level is True:
                    logger.error("Cannot get water level, stop refill")
                    await self._stop_pwm()
                else:
                    await self._start_pwm()
            await asyncio.sleep(float(self._interval_ms) / 1000)

        await self._stop_pwm()
        self._stop_event.set()

    async def stop(self):
        self._stop = True
        await self._stop_event.wait()

    async def _start_pwm(self):
        if not self._is_pwm_stop():
            return

        self._pwm.open()
        self._pwm_task = asyncio.get_event_loop().create_task(
            self._pwm.start())
        logger.info("start refill water")

    async def _stop_pwm(self):
        if self._is_pwm_stop():
            return

        self._pwm.stop()
        self._pwm.close()
        self._pwm_task.cancel()
        try:
            await self._pwm_task
        except asyncio.CancelledError:
            logger.info("stop refill water")
        self._pwm_task = None

    def _is_pwm_stop(self):
        return False if self._pwm_task is not None else True

    async def command_callback(self, data):
        cmd = data['command']
        if cmd == 'get':
            return self._status()
        elif cmd == 'start':
            self._pause = False
            return {'status': 'ok'}
        elif cmd == 'stop':
            self._pause = True
            return {'status': 'ok'}

        return {"status": "error", "message": "Unknown command '%s'" % cmd}

    def _status(self):
        return {"status": "ok", "stop": self._is_pwm_stop()}


class RefillClient(object):
    def __init__(self, bus):
        self._bus = bus

    async def stop(self):
        try:
            response = await self._bus.req('tank.refill', {'command': 'stop'})
            if response['status'] != 'ok':
                logger.warn("Cannot stop 'tank.refill': %s",
                            response['message'])
                return False
            return True
        except futures.TimeoutError:
            logger.warn("Request stop 'tank.refill' timeout")
            return False

    async def start(self):
        try:
            response = await self._bus.req('tank.refill', {'command': 'start'})
            if response['status'] != 'ok':
                logger.warn("Cannot start 'tank.refill': %s", response['message'])
                return False
            return True
        except futures.TimeoutError:
            logger.warn("Request start 'tank.refill' timeout")
            return False

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from lib.tio import tio
from periphery import GPIO
import asyncio


class PWM(tio.IO):
    """ PWM interface
    Attributes:
        dutycycle (float): 0 - 1 (0% - 100%)
        frequency (int): hz
    """

    def open(self):
        raise NotImplementedError

    def close(self):
        raise NotImplementedError

    async def start(self):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError


class PWMConfig(object):
    def __init__(self):
        self.dutycycle = 0
        self.frequency = 0


class SWPWM(PWM):
    """ Software PWM
    """

    def __init__(self, gpio_pin, config):
        """
        Args:
            gpio_pin (int): gpio pin number this PWM used
            config (PWMConfig): configuration for pwm
        """
        self._gpio_pin = gpio_pin
        self._dutycycle = config.dutycycle
        self._freq = config.frequency
        self._gpio = None
        self._lock = None
        self._stop = False
        self._stop_event = asyncio.Event()

    def open(self):
        self._lock = asyncio.Lock()
        self._gpio = GPIO(self._gpio_pin, "out")

    def close(self):
        self._gpio = GPIO(self._gpio_pin, "in")

    @property
    def dutycycle(self):
        """
        dutycycle (float): 0 - 1 (0% - 100%)
        """
        return self._dutycycle

    @dutycycle.setter
    def dutycycle(self, dutycycle):
        if not 0 <= dutycycle <= 1:
            raise ValueError("Duty cycle should be ranged in 0 and 1")
        self._lock.acquire()
        self._dutycycle = dutycycle
        self._lock.release()

    @property
    def frequency(self):
        """
        frequency (int): hz
        """
        return self._freq

    @frequency.setter
    def frequency(self, freq):
        self._lock.acquire()
        self._freq = freq
        self._lock.release()

    async def start(self):
        self._stop = False
        while not self._stop:
            await self._lock
            on_time = self._dutycycle / self._freq
            off_time = (1 - self._dutycycle) / self._freq
            self._lock.release()
            if on_time > 0:
                self._gpio.write(True)
                await asyncio.sleep(on_time)
            if off_time > 0:
                self._gpio.write(False)
                await asyncio.sleep(off_time)
            if on_time == 0 and off_time == 0:
                await asyncio.sleep(1)
        self._stop_event.set()

    async def stop(self):
        self._stop = True
        await self._stop_event.wait()

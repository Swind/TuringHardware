#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from periphery import GPIO
from hardware.sensor import Sensor


class WaterDetector(Sensor):
    """ water detector driver
    """

    def __init__(self, gpio_pin):
        self._gpio_pin = gpio_pin
        self._gpio = None
        self._is_connected = False

    def connect(self):
        self._gpio = GPIO(self._gpio_pin, "in")
        self._is_connected = True
        return True

    def disconnect(self):
        self._is_connected = False
        self._gpio = None
        return True

    def is_connected(self):
        return self._is_connected

    def is_water_full(self):
        """
        Returns:
            bool: return True if detect water full, otherwise return False
        """
        return self._gpio.read()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from logzero import logger
from hardware.max31865 import MAX31865
from hardware.max31856 import MAX31856, TC
from hardware.pwm import SWPWM, PWMConfig
from hardware.smoothie import Smoothie
from hardware.extruder import Extruder
from hardware.spi import HWSPI, SPIConfig
from hardware.uart import UART, UARTConfig


class HWManager(object):
    """ hardware manager (like Linux device tree)
    """

    def __init__(self):
        self._hardwares = {}

    def import_config(self, loop, configs):
        """
        Args:
            loop (asyncio.loop): used by hardware
            configs (dict): hardware configuration
        """
        for config in configs:
            hardware_type = list(config.keys())[0]
            if hardware_type not in HARDWARE_MAPPING:
                logger.error("Cannot resolve '%s' type", hardware_type)
                continue
            driver = HARDWARE_MAPPING[hardware_type](config[hardware_type],
                                                     self, loop)

            name = config[hardware_type]['name']
            if driver is not None:
                logger.info("Create hardware instance '%s'", name)
                self._hardwares[name] = driver
            else:
                logger.info("Cannot create hardware instance '%s'", name)

    def find_hardware(self, name):
        if name not in self._hardwares:
            return None
        return self._hardwares[name]


def create_max31856(hardware_config, hwm, _):
    tc_type = hardware_config['tc_type']
    dev = hardware_config['dev']

    if tc_type == 'B':
        tc_type = TC.B_TYPE
    elif tc_type == 'E':
        tc_type = TC.E_TYPE
    elif tc_type == 'J':
        tc_type = TC.J_TYPE
    elif tc_type == 'K':
        tc_type = TC.K_TYPE
    elif tc_type == 'N':
        tc_type = TC.N_TYPE
    elif tc_type == 'R':
        tc_type = TC.R_TYPE
    elif tc_type == 'S':
        tc_type = TC.S_TYPE
    elif tc_type == 'T':
        tc_type = TC.T_TYPE
    else:
        logger.error("Unknown '%s' - tc_type: '%s'", hardware_config['name'],
                     hardware_config['tc_type'])
        return None

    spidev = hwm.find_hardware(dev)
    if spidev is None:
        logger.warning("Cannot find hardware '%s' for now", dev)
        return ValueError("Cannot find hardware '%s' for now" % dev)

    return MAX31856(spidev)


def create_max31865(hardware_config, hwm, _):
    dev = hardware_config['dev']
    spidev = hwm.find_hardware(dev)
    if spidev is None:
        logger.warning("Cannot find hardware '%s' for now", dev)
        return None

    return MAX31865(spidev)


def create_pwm(hardware_config, _, loop):
    gpio_pin = hardware_config['gpio']
    config = PWMConfig()
    config.dutycycle = hardware_config['dutycycle']
    config.frequency = hardware_config['frequency']
    return SWPWM(gpio_pin, config, loop)


def create_smoothie(hardware_config, hwm, _):
    dev = hardware_config['dev']
    uartdev = hwm.find_hardware(dev)
    if uartdev is None:
        logger.warning("Cannot find hardware '%s' for now",
                       hardware_config['name'])
        return None

    return Smoothie(uartdev)


def create_extruder(hardware_config, hwm, _):
    dev = hardware_config['dev']
    uartdev = hwm.find_hardware(dev)
    if uartdev is None:
        logger.warning("Cannot find hardware '%s' for now",
                       hardware_config['name'])
        return None

    return Extruder(uartdev)


def create_hwspi(hardware_config, *_):
    spi_config = SPIConfig()
    spi_config.speed = hardware_config['speed']
    spi_config.mode = hardware_config['mode']
    number = hardware_config['number']
    chipselect = hardware_config['chipselect']
    return HWSPI(number, chipselect, spi_config)


def create_uart(hardware_config, *_):
    uart_config = UARTConfig()
    uart_config.baudrate = hardware_config['baudrate']
    uart_config.rtscts = hardware_config['rtscts']
    uart_config.dsrdtr = hardware_config['dsrdtr']
    uart_config.read_timeout = hardware_config['read_timeout']
    uart_config.write_timeout = hardware_config['write_timeout']
    return UART(hardware_config['devpath'], uart_config)


HARDWARE_MAPPING = {
    "max31856": create_max31856,
    "max31865": create_max31865,
    "swpwm": create_pwm,
    "smoothie": create_smoothie,
    "extruder": create_extruder,
    "hwspi": create_hwspi,
    "uart": create_uart
}

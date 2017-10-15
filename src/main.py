#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import asyncio
from contextlib import suppress

import yaml

from bus.nats_bus import NatsBus
from hardware.hw_manager import HWManager
from services.service_manager import ServiceManager


async def main():

    parser = argparse.ArgumentParser(description="Turing hardware")
    parser.add_argument(
        'configuration', help='Turing hardware and service configuraiton')
    args = parser.parse_args()

    with open(args.configuration, 'r') as file:
        configuration = yaml.load(file.read())

    hwm = HWManager()
    hwm.import_config(configuration['hardwares'])

    bus_config = configuration['bus']
    bus = NatsBus(bus_config['host'], bus_config['port'])
    await bus.start()

    svm = ServiceManager()
    svm.import_config(configuration['services'], hwm, bus)
    svm.start_all_services()

    while True:
        await asyncio.sleep(1)

    await svm.stop_all_servies()


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    pending = asyncio.Task.all_tasks()
    for task in pending:
        task.cancel()
        with suppress(asyncio.CancelledError):
            loop.run_until_complete(task)

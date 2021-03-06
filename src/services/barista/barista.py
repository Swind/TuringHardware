# -*- coding: utf-8 -*-

import time
import math
import asyncio
from logzero import logger
from services.barista.point import Point
from services.barista.point_translator import point_to_gcode
from services.barista.point_translator import point_to_hcode
from services.refill_service import RefillClient
from services.output_temp_service import OutputTempClient
from services.tank_temp_service import TankTempClient


class WasteWaterPosition(Point):
    def __init__(self, x, y, z):
        super(WasteWaterPosition, self).__init__()
        self.x = x
        self.y = y
        self.z = z


class WaterTransformer(object):
    def __init__(self, pid, output_temp):
        self._pid = pid
        self._output_temp = output_temp
        self._accumulated_water = 0
        self._current_target_temperature = None
        self._current_percentage = None
        self.low_temperature = None
        self.high_temperature = None
        self._previous_time = None
        self.reset()

    def reset(self):
        self._accumulated_water = 0
        self._current_target_temperature = None
        self._current_percentage = None
        self._previous_time = None
        self._pid.reset()

    async def transform(self, point):
        if point.t is not None and point.t != self._current_target_temperature:
            self._current_target_temperature = point.t
            self._current_percentage = (
                self._current_target_temperature - self.low_temperature) / (
                    self.high_temperature - self.low_temperature)
            self.reset()

        if point.e is not None:
            if self._accumulated_water >= 10:
                temperature = await self._output_temp.get_temperature()
                diff_time = 0
                if self._previous_time is not None:
                    current_time = time.time()
                    diff_time = current_time - self._previous_time
                    self._previous_time = current_time
                percentage = self._current_percentage + self._pid(
                    temperature, self._current_target_temperature,
                    diff_time) / 100
                if percentage > 1:
                    percentage = 1
                elif percentage < 0:
                    percentage = 0
                self._accumulated_water = 0

            point.e1 = point.e * percentage
            point.e2 = point.e - point.e1
            self._accumulated_water += point.e


class TimeTransformer(object):
    def __init__(self, x=0, y=0, z=0):
        self._position = Point.create_point(x=x, y=y, z=z)

    async def transform(self, point):
        if point.time is not None:
            return
        distance = self._calc_distance(point)
        if distance == 0:
            point.time = point.f
        else:
            point.time = distance * 60 / point.f
        self.set_position(x=point.x, y=point.y, z=point.z)

    def set_position(self, x=None, y=None, z=None):
        if x is not None:
            self._position.x = x
        if y is not None:
            self._position.y = y
        if z is not None:
            self._position.z = z

    def _calc_distance(self, point):
        distance = 0
        if point.x is not None:
            distance += (point.x - self._position.x)**2
        if point.y is not None:
            distance += (point.y - self._position.y)**2
        if point.z is not None:
            distance += (point.z - self._position.z)**2
        return math.sqrt(distance)


class Barista(object):
    def __init__(self, moving_dev, extruder_dev, mix_pid_dev,
                 waste_water_position, default_moving_speed, bus):
        self._commands = {
            "wait": self._create_wait,
            "calibration": self._create_calibration,
            "waste_water": self._create_waste_water,
            "mix": self._create_mix,
            "home": self._create_home
        }

        self._moving_dev = moving_dev
        self._extruder_dev = extruder_dev
        self._waste_water_position = waste_water_position
        self._default_moving_speed = 5000
        self._bus = bus
        self._refill = RefillClient(bus)
        self._output_temp = OutputTempClient(bus)
        self._tank_temp = TankTempClient(bus)
        self._water_transformer = WaterTransformer(mix_pid_dev,
                                                   self._output_temp)
        self._time_transformer = TimeTransformer()

        self._high_temperature = None
        self._low_temperature = None
        self._accumulated_water = 0

        self._stop = False
        self._stop_event = asyncio.Event()
        self._queue = asyncio.Queue(maxsize=1)

        self._position = Point.create_point(x=0, y=0, z=0)

    def _create_wait(self, param):
        _time = param['time']

        async def implement():
            nonlocal self
            nonlocal _time
            while not self._stop and _time > 0:
                asyncio.sleep(1)
                _time -= 1
            return True

        return implement

    def _create_calibration(self, _):
        async def implement():
            nonlocal self
            # move
            await self._move_to_waste_water_position()

            async def test_stable_temperature(self, points):
                pre_temp = await self._output_temp.get_temperature()
                if pre_temp is None:
                    return None
                while True:
                    await self._handle_point(points)
                    temp = await self._output_temp.get_temperature()
                    if temp is None:
                        return None

                    slope = abs((temp - pre_temp) / 5)
                    if slope > 3 / 5:
                        pre_temp = temp
                        continue
                    return temp

            # e2
            points = [Point.create_point(e2=0.6, time=0.1)] * 50
            self._water_transformer.high_temperature = await test_stable_temperature(
                self, points)
            if self._high_temperature is None:
                return False

            # e1
            points = [Point.create_point(e1=0.6, time=0.1)] * 50
            self._water_transformer.low_temperature = await test_stable_temperature(
                self, points)
            if self._low_temperature is None:
                return False
            return True

        return implement

    def _create_waste_water(self, _):
        async def implement():
            nonlocal self
            await self._move_to_waste_water_position()
            points = [Point.create_point(e1=3, e2=3, t=1)] * 10
            self._handle_point(points)
            return True

        return implement

    def _create_mix(self, param):
        target_temperature = param['t']

        async def implement():
            nonlocal self
            await self._move_to_waste_water_position()
            points = [
                Point.create_point(e=0.5, t=target_temperature, time=0.1)
            ] * 20
            previous_temperature = await self._output_temp.get_temperature()
            while True:
                self._handle_point(points)
                current_temperature = await self._output_temp.get_temperature()
                diff = abs(current_temperature - target_temperature)
                slope = abs(current_temperature - previous_temperature)
                if diff < 0.5 and slope < 3 / 5:
                    break
                previous_temperature = current_temperature
            return True

        return implement

    def _create_home(self, _):
        async def implement():
            nonlocal self
            self._moving_dev.send('G28')
            self._time_transformer.set_position(x=0, y=0, z=0)
            return True

        return implement

    def _create_handle_points(self, point_param):
        async def implement():
            nonlocal self
            nonlocal point_param
            point = [Point.create_point(*point_param)]
            await self._handle_point(point)
            return True

        return implement

    async def _handle_point(self, points):
        for point in points:
            await self._water_transformer.transform(point)
            await self._time_transformer.transform(point)

            gcode = point_to_gcode(point)
            hcode = point_to_hcode(point)

            if gcode is not None:
                self._moving_dev.send(gcode)
            if hcode is not None:
                self._extruder_dev.send(hcode)

            if gcode is not None:
                while self._moving_dev.recv() != 'ok':
                    await asyncio.sleep(0.1)
            if hcode is not None:
                while self._extruder_dev.recv() != 'ok':
                    await asyncio.sleep(0.1)

    async def start(self):
        await self._bus.reg_rep('barista', self.command_callback)
        self._moving_dev.connect(3)
        self._extruder_dev.connect(3)

        # HOME, Set Unit to Millimeters,
        # Set to Absolute Positioning, Set extruder to relative mode
        for cmd in ['G28', 'G21', 'G90', 'M83']:
            self._moving_dev.send(cmd)

        while True:
            params = await self._queue.get()
            await self.brew(params)

    async def brew(self, params):
        await self._refill.stop()

        # XXX: maybe from config
        if self._water_transformer.low_temperature is None:
            self._water_transformer.low_temperature = 20
        if self._water_transformer.high_temperature is None:
            self._water_transformer.high_temperature = await self._tank_temp.get_temperature(
            )

        commands = []
        for param in params:
            if param['type'] == 'command' and param['name'] in self._commands:
                commands.append(self._commands[param['name']](param))
            elif 'point' in param:
                commands.append(self._create_handle_points(param['point']))
            else:
                logger.error('Invalid input point %s', param)
                continue

        self._reset()
        for command in commands:
            await command()

        await self._refill.start()

    async def command_callback(self, data):
        cmd = data['command']
        if cmd == 'get':
            return await self._status()
        elif cmd == 'brew':
            points = data['points']
            try:
                self._queue.put_nowait(points)
                return {'status': 'ok'}
            except asyncio.QueueFull:
                return {'status': 'error', 'message': 'barista is busy'}

    def _reset(self):
        self._time_transformer.set_position(0, 0, 0)
        self._water_transformer.reset()

    async def _status(self):
        return {'status': 'ok'}

    async def _move_to_waste_water_position(self):
        points = [
            Point.create_move_point(
                x=self._waste_water_position.x,
                y=self._waste_water_position.y,
                z=self._waste_water_position.z,
                f=self._default_moving_speed)
        ]
        await self._handle_point(points)

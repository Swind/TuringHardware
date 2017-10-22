#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from lib.proto.textproto import TextProto


class Smoothie(object):
    def __init__(self, uartdev):
        """
        Args:
            uartdev (UART)
        """
        self._uart = uartdev
        self._textproto = TextProto(self._uart, self._uart, 64)

    def connect(self, retry_times):
        """ Connect to smoothie
        Try to connect smoothie and check it is worked or not.

        Args:
            retry_times (int): retry times for connect to Smoothie board
        Returns:
            bool: True if connect success, otherwise return False
        """
        for _ in range(retry_times):
            self._uart.open()
            self.send('G')
            if self.recv() != 'ok':
                self._uart.close()
                continue

            return True
        return False

    def disconnect(self):
        self._uart.close()

    def send(self, data):
        """
        Args:
            data (str): Gcode to write
        """
        self._textproto.writeline(data)

    def recv(self):
        return self._textproto.readline().strip()

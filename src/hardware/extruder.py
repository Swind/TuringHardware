#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from lib.proto.textproto import TextProto

class Extruder(object):
    def __init__(self, uartdev):
        """
        Args:
            uartdev (UART)
        """
        self._uart = uartdev
        self._textproto = TextProto(self._uart, self._uart, 64)

    def connect(self, retry_times):
        """ Connect to extruder
        Try to connect extruder and check the function is worked or not
        Args:
            retry_times (int): retry times for connect to Smoothie board
        """
        for _ in range(retry_times):
            self._uart.open()
            self.send('')
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
            data (str): Hcode to write
        """
        self._textproto.writeline(data)

    def recv(self):
        return self._textproto.readline().strip()

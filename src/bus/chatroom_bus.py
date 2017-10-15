#!/usr/bin/env python3

from chatroom import 
from logzero import logger
import retrying
import json


class ChatroomBus(object):
    def __init__(self, host, port, path):
        self._host = host
        self._chartroom_client = ChatroomClient(path, server_name=host)
        self._retry_times = 0

    @retrying.retry
    async def start(self):
        try:
            logger.info("Try to connect to chatroom server {}, {} times".format(self._host, self._retry_times))
            await self._chatroom_client.connect()
        except TimeoutError as e:
            self._retry_times += 1
            logger.error("Cannot connect to nats server '%s'", self._url)
            raise e

        self._retry_times = 0
        logger.info("Connect to nats server '%s' successfully", self._url)

    async def req(self, payload, timeout=1):
        if not self._nats_client.is_connected:
            return None
        return await self._nats_client.timed_request(
            self._path + '.rep', json.dumps(payload).encode('utf-8'), timeout)

    async def reg_rep(self, callback):
        return await self.reg_sub(self._path + '.rep', callback)

    async def pub(self, payload):
        if not self._nats_client.is_connected:
            return False
        await self._nats_client.publish(self._path + '.pub',
                                        json.dumps(payload).encode('utf-8'))
        return True

    async def reg_sub(self, callback):
        if not self._nats_client.is_connected:
            return False
        await self._nats_client.subscribe(
            self._path + '.pub', cb=self.cb_wrap(callback))
        return True

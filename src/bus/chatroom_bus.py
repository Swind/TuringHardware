#!/usr/bin/env python3

from chatroom.async_client import AsyncClient as ChatroomClient
from logzero import logger
import retrying
import json

class ChatroomBus(object):
    def __init__(self, host, port, path, event_loop=None):
        self._host = host
        self._path = path
        self._chatroom_client = ChatroomClient(path, server_name=host, event_loop=event_loop)
        self._retry_times = 0

    async def start(self):
        try:
            logger.info("Try to connect to chatroom server {}, {} times".format(self._host, self._retry_times))
            await self._chatroom_client.connect()
        except TimeoutError as e:
            self._retry_times += 1
            logger.error("Cannot connect to chatroom server '%s'", self._host)
            raise e

        self._retry_times = 0
        logger.info("Connect to chatroom server '%s' successfully", self._host)

    async def req(self, target_path, method, parameters, timeout=1):
        event = await self._chatroom_client.send_rpc_request(
            target=target_path,
            method=method,
            parameters=parameters
        )

        result = await event.wait(timeout)
        return result

    def reg_rep(self, method_name, callback):
        return self._chatroom_client.register_rpc_api(method_name, callback)

    async def pub(self, payload):
        await self._chatroom_client.publish(json.dumps(payload).encode('utf-8'))
        return True

    async def reg_sub(self, path, callback):
        await self._chatroom_client.subscribe(path , callback=callback)
        return True

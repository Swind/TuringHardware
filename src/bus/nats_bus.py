#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from nats.aio.client import Client as NATS
from nats.aio.errors import ErrConnectionClosed, ErrTimeout, ErrNoServers
from logzero import logger
import json
import uuid


class NatsBus(object):
    def __init__(self, host, port, path):
        self._nats_client = NATS()
        self._url = "nats://%s:%d" % (host, port)
        self._path = path
        self.rpc_apis = {}

    async def on_request(self, msg):
        error = None 
        result = None 

        data = json.loads(msg.data.decode())

        id = data.get('id')
        method = data.get('method')
        parameters = data.get('parameters')

        callback = self.rpc_apis.get(method)
        if callback is None:
            error = "The method is not existing".format(method)
        else:
            result = await callback(parameters)

        if error is not None:
            await self.pub(msg.reply, dict(
                id=id,
                error=error
            ))
        else:
            await self.pub(msg.reply, dict(
                id=id,
                result=result
            ))

    async def start(self):
        retry_times = 0
        while True:
            try:
                logger.info("Try to connect to nats server '%s', %d times",
                            self._url, retry_times)
                await self._nats_client.connect(servers=[self._url])
                await self._nats_client.subscribe(self._path, cb=self.on_request)
                break
            except ErrNoServers:
                retry_times += 1
                logger.error("Cannot connect to nats server '%s'", self._url)

        logger.info("Connect to nats server '%s' successfully", self._url)

    async def req(self, target_path, method, parameters, timeout=1):
        if not self._nats_client.is_connected:
            return None

        id = str(uuid.uuid1())
        payload = dict(
                id=id,
                method=method,
                parameters=parameters
        ) 
        return await self._nats_client.timed_request(
                target_path, 
                json.dumps(payload).encode('utf-8'), 
                timeout)

    async def reg_rpc_api(self, name, callback):
        self.rpc_apis[name] = callback

    async def pub(self, path, payload):
        if not self._nats_client.is_connected:
            return False

        await self._nats_client.publish(self._path + '.pub',
                                        json.dumps(payload).encode('utf-8'))
        return True

    def cb_wrap(self, callback):
        return async def wrap(msg):
            data = json.loads(msg.data.decode())
            callback(data)

    async def reg_sub(self, path, callback):
        if not self._nats_client.is_connected:
            return False

        await self._nats_client.subscribe(
            path + '.pub', 
            cb=self.cb_wrap(callback))

        return True

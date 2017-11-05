from nats.aio.client import Client as NATS
from nats.aio.errors import ErrConnectionClosed, ErrTimeout, ErrNoServers

from logzero import logger
from lib.retrying import retry

import json
import uuid

def _log_retry_attempt_times(self, message):

    def wrapper(attempt_times):
        logger.info("{}, {} times".format(message, attempt_times))

    return wrapper

class NatsBus(object):
    def __init__(self, host, port, path):
        self._nats_client = NATS()
        self._url = "nats://%s:%d" % (host, port)
        self._path = path
        self.rpc_apis = {}

    ################################################################################
    #
    #   Request / Response
    #
    ################################################################################
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

    async def reg_rpc_api(self, name, callback):
        self.rpc_apis[name] = callback

    @retry(before_attempts=_log_retry_attempt_times("Try to connect to nats server"))
    async def start(self):
        try:
            await self._nats_client.connect(servers=[self._url])
            await self._nats_client.subscribe(self._path, cb=self.on_request)
        except ErrNoServers as e:
            logger.error("Cannot connect to nats server '%s'", self._url)
            raise e

        logger.info("Connect to nats server '%s' successfully", self._url)

    def check_connection(self):
        if not self._nats_client.is_connected:
            raise ConnectionError("The connection has not been established")
        
        return True

    async def req(self, target_path, method, parameters, timeout=1):
        self.check_connection()

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

    ################################################################################
    #
    #   Publish / Subscribe
    #
    ################################################################################
    async def pub(self, path, payload):
        self.check_connection()

        await self._nats_client.publish(self._path + '.pub',
                                        json.dumps(payload).encode('utf-8'))
        return True

    async def reg_sub(self, path, callback):
        self.check_connection()

        async def wrap(msg):
            data = json.loads(msg.data.decode())
            callback(data)

        await self._nats_client.subscribe(
            path + '.pub', 
            cb=wrap)

        return True

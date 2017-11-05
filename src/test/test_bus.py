import pytest
from bus.chatroom_bus import ChatroomBus
from threading import Event


def test_send_request(server_name, server, event_loop):
    def callback(data):
        print("Received rpc request")
        return "Hello world! {}".format(data)

    async def async_test_send_request(loop):
        path = "turing.testing.send_requests.bus"
        bus = ChatroomBus(host=server_name, path=path, port=None, event_loop=loop)
        bus.reg_rep("hello_world", callback)
        await bus.start()

        result = await bus.req(path, "hello_world", {"data": 1})
        print("Send request done")
        assert result == "Hello world! 1"

        return True

    result = event_loop.run_until_complete(async_test_send_request(event_loop))
    assert result is True


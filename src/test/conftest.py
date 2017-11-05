import pytest
import threading
from chatroom.server import Server

import asyncio

@pytest.fixture(scope="session")
def server_name():
    return 'turing-testing'


def _start_server(server):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    server.start(handle_signals=False)


@pytest.fixture(scope="session")
def server(request, server_name):
    server = Server(server_name, "127.0.0.1", 6543, "0.0.1")
    server_thread = threading.Thread(target=_start_server, args=[server], daemon=True)
    server_thread.start()
    yield server

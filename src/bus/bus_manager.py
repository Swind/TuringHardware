from bus.nats_bus import NatsBus
from bus.chatroom_bus import ChatroomBus

class BusManager:
    NATS = "nats"
    CHATROOM = "chatroom"

    def __init__(self):
        self.host = None
        self.port = None

    def import_config(self, config):
        self.host =  config['host']
        self.port = config['port']
        self.bus_type = config['type']

    def create_bus_client(self, path):
        if self.bus_type == self.NATS:
            self._create_nats_bus_client(path)
        elif self.bus_type == self.CHATROOM:
            self._create_chatroom_bus_client(path)
        else:
            raise RuntimeError("Unknown bus type {}".format(self.bus_type))

    def _create_nats_bus_client(self, path):
        return NatsBus(self.host, self.port, path)

    def _create_chatroom_bus_client(self, path):
        return ChatroomBus(self.host, self.port, path)

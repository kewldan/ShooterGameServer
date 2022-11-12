import hashlib
import struct
import threading
import socket
from uuid import uuid1, UUID


class ClientEventType:
    DISCONNECTED = 1
    CONNECTED = 2


class ClientPacketTypes:
    HANDSHAKE = 2
    UPDATE = 4
    EXIT = 8


class ServerPacketTypes:
    HANDSHAKE = 1
    UPDATE = 3
    KICK = 5


class PacketTypes:
    CLIENT_SIDE = ClientPacketTypes
    SERVER_SIDE = ServerPacketTypes


class Packet:
    def __init__(self, data: bytes):
        self.__validated = None
        self.__length = data[1] << 8 | data[0]
        self.__sign = data[2:18]
        self.__type = data[19] << 8 | data[18]
        self.__payload = data[20:]

    def isValid(self) -> bool:
        if self.__validated is None:
            calculated_sign = hashlib.md5(self.__payload).digest()
            self.__validated = calculated_sign == self.__sign

        return self.__validated

    def getPayload(self) -> bytes:
        return self.__payload

    def getType(self) -> int:
        return self.__type

    def getSign(self) -> bytes:
        return self.__sign

    def __str__(self) -> str:
        return f'Packet(length={self.__length},type={self.__type},valid={self.isValid()})'


class Server:
    def __init__(self, port: int, max_connections: int = 16):
        self.port = port

        self.socket = socket.socket()
        self.socket.bind(('', port))
        self.socket.listen(max_connections)

        self.packet_handler = None
        self.client_handler = None
        self.clients = {}

    def start(self):
        while True:
            conn, addr = self.socket.accept()
            client_id = uuid1()
            client = Client(conn, addr, self, client_id)
            self.clients[client_id] = client
            self.client_handler(ClientEventType.CONNECTED, client)

    def set_packet_handler(self, handler):
        self.packet_handler = handler

    def set_client_handler(self, handler):
        self.client_handler = handler

    def stop(self):
        for client in self.clients:
            client.connection.close()
        self.socket.close()
        print("Shutdown")


class Client:
    def __init__(self, connection: socket.socket, address, server: Server, my_id: UUID):
        self.connection = connection
        self.address = address
        self.master = server
        self.id = my_id
        self.authorized = False
        self.packetListener = threading.Thread(target=self.listen_packets, args=(self,), daemon=True)
        self.packetListener.start()

    def listen_packets(self, _):
        while True:
            try:
                data = self.connection.recv(65536)
            except ConnectionResetError:
                break
            if data is None or not data:
                break
            else:
                packet = Packet(data)
                self.master.packet_handler(packet, self)

        self.connection.close()
        del self.master.clients[self.id]
        self.master.client_handler(ClientEventType.DISCONNECTED, self)

    def send_packet(self, payload, packet_type: int):
        data = []
        data += struct.pack('h', 18 + len(payload))
        data += list(hashlib.md5(bytes(payload)).digest())
        data += struct.pack('h', packet_type)
        data += payload

        self.connection.send(bytes(data))
        pass

    def __str__(self) -> str:
        return f'Client(id={self.id},auth={self.authorized})'

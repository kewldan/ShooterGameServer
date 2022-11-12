import hashlib
import threading
import socket
from uuid import uuid1, UUID


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

        self.handlers = []
        self.clients = {}

    def start(self):
        while True:
            conn, addr = self.socket.accept()
            client_id = uuid1()
            client = Client(conn, addr, self, client_id)
            self.clients[client_id] = client
            print("New client with id:", client_id)

    def add_handler(self, handler):
        self.handlers.append(handler)

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
        self.packetListener = threading.Thread(target=self.listen_packets, args=(self, ), daemon=True)
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
                for handler in self.master.handlers:
                    handler(packet)

        self.connection.close()
        del self.master.clients[self.id]
        print("Client disconnected with id:", self.id)

    def __str__(self) -> str:
        return f'Client(id={self.id})'



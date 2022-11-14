import random
import struct
import threading
import socket


class ClientEventType:
    DISCONNECTED = 1
    CONNECTED = 2


class ClientPacketTypes:
    HANDSHAKE = 2
    UPDATE = 4


class ServerPacketTypes:
    HANDSHAKE = 1
    UPDATE = 3
    MESSAGE = 5


class Packet:
    def __init__(self, payload_length: int, packet_type: int, packet_payload_buffer: bytes):
        self.__length = payload_length
        self.__type = packet_type
        self.__payload = packet_payload_buffer

    def getPayload(self) -> bytes:
        return self.__payload

    def getType(self) -> int:
        return self.__type

    def __str__(self) -> str:
        return f'Packet(length={self.__length},type={self.__type})'


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
            client_id = str(random.randint(1, 2 ** 24))
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
    def __init__(self, connection: socket.socket, address, server: Server, my_id: str):
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
                packet_header_buffer = self.connection.recv(4)
                if not packet_header_buffer:
                    break
                else:
                    payload_length = packet_header_buffer[1] << 8 | packet_header_buffer[0]
                    packet_type = packet_header_buffer[3] << 8 | packet_header_buffer[2]

                    packet_payload_buffer = self.connection.recv(payload_length)
                    if not packet_payload_buffer:
                        break
                    else:
                        packet = Packet(payload_length, packet_type, packet_payload_buffer)
                        self.master.packet_handler(packet, self)
            except ConnectionResetError:
                break
            except ConnectionAbortedError:
                break
        self.connection.close()
        del self.master.clients[self.id]
        self.master.client_handler(ClientEventType.DISCONNECTED, self)

    def send_packet(self, payload, packet_type: int):
        data = []
        data += struct.pack('h', len(payload))
        data += struct.pack('h', packet_type)
        data += payload

        self.connection.send(bytes(data))
        pass

    def __str__(self) -> str:
        return f'Client(id={self.id},auth={self.authorized})'

import random
import struct
import threading
import socket
import time


class ClientEventType:
    DISCONNECTED = 1
    CONNECTED = 2


class ClientPacketTypes:
    HANDSHAKE = 2
    UPDATE = 4
    MESSAGE = 6
    GET_PLAYER = 8


class ServerPacketTypes:
    HANDSHAKE = 1
    UPDATE = 3
    MESSAGE = 5
    KICK = 7
    PLAYER_INFO = 9


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

    def getLength(self):
        return self.__length


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
        try:
            while True:
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
        except ConnectionAbortedError:
            pass
        except ConnectionResetError:
            pass
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

    def send_update(self, players):
        output = []
        output += [len(players) - 1]
        for player in players:
            if player.client.id != self.id:
                output += list(struct.pack('I', int(player.client.id)))
                output += list(struct.pack('f', player.x))
                output += list(struct.pack('f', player.y))
                output += list(struct.pack('f', player.z))
                output += list(struct.pack('f', player.rx))
                output += list(struct.pack('f', player.ry))
        self.send_packet(output, ServerPacketTypes.UPDATE)

    def send_handshake(self):
        output = []
        output += list(struct.pack('I', int(self.id)))
        self.send_packet(output, ServerPacketTypes.HANDSHAKE)

    def send_message(self, sender: str, message: str):
        output = []
        output += [len(sender)]
        output += list(sender.encode())
        output += [len(message)]
        output += list(message.encode())
        self.send_packet(output, ServerPacketTypes.MESSAGE)

    def kick(self, reason: str):
        output = []
        output += list(reason.encode())
        self.send_packet(output, ServerPacketTypes.KICK)
        time.sleep(0.5)
        self.connection.close()

    def send_player_info(self, id: int, nickname: str):
        output = []
        output += list(struct.pack('I', id))
        output += list(nickname.encode())
        self.send_packet(output, ServerPacketTypes.PLAYER_INFO)

    def __str__(self) -> str:
        return f'Client(id={self.id},auth={self.authorized})'


class Player:
    def __init__(self, client: Client, nickname: str):
        self.nickname = nickname
        self.client = client
        self.x = 0.0
        self.y = 0.0
        self.z = 0.0
        self.rx = 0.0
        self.ry = 0.0

    def __str__(self) -> str:
        return f'Player(name={self.nickname},client={self.client},pos=({self.x},{self.y},{self.z}))'

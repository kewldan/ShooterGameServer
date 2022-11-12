from ShooterGame import *
import threading
import struct

players = []


class Player:
    def __init__(self, client: Client, nickname: str):
        self.nickname = nickname
        self.client = client
        self.x = 0
        self.y = 0
        self.z = 0
        self.rx = 0
        self.ry = 0

    def __str__(self) -> str:
        return f'Player(name={self.nickname},client={self.client})'


def packet_handler(packet: Packet, client: Client):
    data = packet.getPayload()
    if packet.getType() == PacketTypes.CLIENT_SIDE.HANDSHAKE:
        if not client.authorized:
            nickname_length = data[0]
            nickname = data[1:nickname_length + 1].decode()
            players.append(Player(client, nickname))
            print("Client became player now, nickname:", nickname)
            client.authorized = True
    if packet.getType() == PacketTypes.CLIENT_SIDE.UPDATE:
        if client.authorized:
            for player in players:
                if player.client.id == client.id:
                    player.x = struct.unpack('f', data[:4])
                    player.y = struct.unpack('f', data[4:8])
                    player.z = struct.unpack('f', data[8:12])
                    player.rx = struct.unpack('f', data[12:16])
                    player.ry = struct.unpack('f', data[16:])

                    send_update_to_client(client)
                    print(player.x, player.y, player.z, player.rx, player.ry)
                    return
        print("Invalid player")


def send_update_to_client(client: Client):
    output = []
    for player in players:
        if player.client.id != client.id:
            output += list(struct.pack('f', player.x))
            output += list(struct.pack('f', player.y))
            output += list(struct.pack('f', player.z))
            output += list(struct.pack('f', player.rx))
            output += list(struct.pack('f', player.ry))
            output += len(player.nickname)
            output += list(player.nickname.encode())
    client.send_packet(output, PacketTypes.SERVER_SIDE.UPDATE)


def client_handler(type: ClientEventType, client: Client):
    if type == ClientEventType.CONNECTED:
        print("Client connected", client.id)
    elif type == ClientEventType.DISCONNECTED:
        for player in players:
            if player.client.id == client.id:
                players.remove(player)
                print("Player disconnected", client.id)
                return
        print("Not authed player disconnected", client.id)


if __name__ == '__main__':
    server = Server(23403)
    server.set_packet_handler(packet_handler)
    server.set_client_handler(client_handler)
    server_process = threading.Thread(target=server.start, daemon=True)
    server_process.start()

    while True:
        try:
            text = input("> ")
            spl = text.split()
            cmd = spl[0].lower()
            if cmd == 'stop':
                server.stop()
                break
            elif cmd == 'players':
                for player in players:
                    print(player)
                if not len(players):
                    print("No players")
            else:
                print("Unknown command")
        except KeyboardInterrupt:
            pass

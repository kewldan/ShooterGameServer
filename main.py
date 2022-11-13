from ShooterGame import *
import threading
import struct

players = []


class Player:
    def __init__(self, client: Client, nickname: str):
        self.nickname = nickname
        self.client = client
        self.x = 0.0
        self.y = 0.0
        self.z = 0.0
        self.rx = 0.0
        self.ry = 0.0

        self.deaths = 0
        self.kills = 0
        self.ammo = 0
        self.hp = 100

    def __str__(self) -> str:
        return f'Player(name={self.nickname},client={self.client},pos=({self.x},{self.y},{self.z}))'


def packet_handler(packet: Packet, client: Client):
    data = packet.getPayload()
    if packet.getType() == ClientPacketTypes.HANDSHAKE:
        if not client.authorized:
            nickname_length = data[0]
            nickname = data[1:nickname_length + 1].decode()
            players.append(Player(client, nickname))
            client.authorized = True
            send_handshake_to_client(client)
            print(nickname, "connected")
    if packet.getType() == ClientPacketTypes.UPDATE:
        if client.authorized:
            for player in players:
                if player.client.id == client.id:
                    player.x = struct.unpack('f', data[:4])[0]

                    player.y = struct.unpack('f', data[4:8])[0]
                    player.z = struct.unpack('f', data[8:12])[0]
                    player.rx = struct.unpack('f', data[12:16])[0]
                    player.ry = struct.unpack('f', data[16:20])[0]

                    send_update_to_client(client)
                    return
        print("Invalid player")


def send_update_to_client(client: Client):
    output = []
    output += [len(players) - 1]
    for player in players:
        if player.client.id != client.id:
            output += list(struct.pack('I', int(client.id)))
            output += list(struct.pack('f', player.x))
            output += list(struct.pack('f', player.y))
            output += list(struct.pack('f', player.z))
            output += list(struct.pack('f', player.rx))
            output += list(struct.pack('f', player.ry))
    client.send_packet(output, ServerPacketTypes.UPDATE)


def send_handshake_to_client(client: Client):
    output = []
    output += list(struct.pack('I', int(client.id)))
    client.send_packet(output, ServerPacketTypes.HANDSHAKE)


def client_handler(type: ClientEventType, client: Client):
    if type == ClientEventType.CONNECTED:
        pass
    elif type == ClientEventType.DISCONNECTED:
        for player in players:
            if player.client.id == client.id:
                players.remove(player)
                print(player.nickname, "disconnected")
                return
        print("Unknown player disconnected")


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
                i = 1
                for player in players:
                    print(str(i) + '.', player)
                    i += 1
                if not len(players):
                    print("No players")
            elif cmd == 'kick':
                if len(spl) == 2:
                    id = int(spl[1]) - 1
                    players[id].client.connection.close()
            else:
                print("Unknown command")
        except KeyboardInterrupt:
            pass

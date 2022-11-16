from ShooterGame import *
import threading
import struct

players = []


def packet_handler(packet: Packet, client: Client):
    payload = packet.getPayload()
    if packet.getType() == ClientPacketTypes.HANDSHAKE:
        if not client.authorized:
            nickname_length = payload[0]
            nickname = payload[1:nickname_length + 1].decode()
            if not nickname == "Server":
                prob_player = get_player_by_name(nickname)
                if not prob_player:
                    players.append(Player(client, nickname))
                    client.authorized = True
                    client.send_handshake()
                    print(nickname, "connected")
                else:
                    client.kick("Nickname already taken")
            else:
                client.kick("Inaccessible nickname")
    if client.authorized:
        sender = get_player_by_id(client.id)
        if sender:
            if packet.getType() == ClientPacketTypes.UPDATE:
                sender.x = struct.unpack('f', payload[:4])[0]

                sender.y = struct.unpack('f', payload[4:8])[0]
                sender.z = struct.unpack('f', payload[8:12])[0]
                sender.rx = struct.unpack('f', payload[12:16])[0]
                sender.ry = struct.unpack('f', payload[16:20])[0]

                client.send_update(players)
            elif packet.getType() == ClientPacketTypes.MESSAGE:
                message = payload.decode()
                for player in players:
                    player.client.send_message(sender.nickname, message)
                print('[' + sender.nickname + ']', message)
            elif packet.getType() == ClientPacketTypes.GET_PLAYER:
                player_id = struct.unpack('I', payload)[0]
                player = get_player_by_id(str(player_id))
                if player:
                    client.send_player_info(player_id, player.nickname)


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


def get_player_by_name(nickname: str) -> Player:
    for player in players:
        if player.nickname == nickname:
            return player


def get_player_by_id(id: str) -> Player:
    for player in players:
        if player.client.id == id:
            return player


if __name__ == '__main__':
    server = Server(23403)
    server.set_packet_handler(packet_handler)
    server.set_client_handler(client_handler)
    server_process = threading.Thread(target=server.start, daemon=True)
    server_process.start()

    while True:
        try:
            line = input("> ")
            spl = line.split()
            if len(spl) > 0:
                cmd = spl[0].lower()
                if cmd == 'stop':
                    server.stop()
                    break
                elif cmd == 'players':
                    for player in players:
                        print(player)
                    if not len(players):
                        print("No players")
                elif cmd == 'kick':
                    if len(spl) >= 2:
                        player = get_player_by_name(spl[1])
                        if player is None:
                            print("Player is not exists")
                            continue
                        reason = "Command kick"
                        if len(spl) > 2:
                            reason = line[len(spl[0]) + len(spl[1]) + 2:]
                        player.client.kick(reason)
                    else:
                        print("Usage: kick [Nickname: str] [Reason: str (Optional)]")
                elif cmd == 'msg':
                    if len(spl) > 2:
                        msg = line[len(spl[0]) + len(spl[1]) + 2:]
                        player = get_player_by_name(spl[1])
                        if player is None:
                            print("Player is not exists")
                            continue
                        player.client.send_message("Server -> " + player.nickname, msg)
                        print("[Server -> " + player.nickname + "]", msg)
                    else:
                        print("Usage: msg [Nickname: str] [Message: str]")
                elif cmd == 'say':
                    if len(spl) > 1:
                        msg = line[len(spl[0]) + 1:]
                        for player in players:
                            player.client.send_message("Server", msg)
                        print("[Server]", msg)
                else:
                    print("Unknown command")
        except KeyboardInterrupt:
            pass

from ShooterGame import *
import threading


def packet_handler(packet: Packet):
    print(packet)
    print(*packet.getPayload())
    print(packet.getPayload().decode())


if __name__ == '__main__':
    server = Server(23403)
    server.add_handler(packet_handler)
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
            elif cmd == 'clients':
                for client in server.clients:
                    print(client)
                if not len(server.clients):
                    print("No clients")
            else:
                print("Unknown command")
        except KeyboardInterrupt:
            pass
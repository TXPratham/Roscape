import socket, struct, json, threading

MCAST_GRP = '239.0.0.1'
MCAST_PORT = 5005

class UDPNode:
    def __init__(self, robot_id, on_message):
        self.robot_id = robot_id
        self.on_message = on_message

        self.send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.send_sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
        self.send_sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)
        try:
            self.send_sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF,
                                      socket.inet_aton('127.0.0.1'))
        except OSError:
            pass

        self.recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.recv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.recv_sock.bind(('', MCAST_PORT))
        mreq = struct.pack('4sL', socket.inet_aton(MCAST_GRP), socket.INADDR_ANY)
        self.recv_sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        threading.Thread(target=self._listen, daemon=True).start()

    def _listen(self):
        while True:
            try:
                data, _ = self.recv_sock.recvfrom(4096)
                msg = json.loads(data.decode())
                if msg.get('robot_id') != self.robot_id:
                    self.on_message(msg)
            except Exception as e:
                print("recv error:", e)

    def broadcast(self, msg):
        self.send_sock.sendto(json.dumps(msg).encode(), (MCAST_GRP, MCAST_PORT))

import sys, time
from comms.udp_node import UDPNode

robot_id = sys.argv[1] if len(sys.argv) > 1 else "amr-1"

def on_msg(msg):
    print(f"[{robot_id}] heard {msg['robot_id']} pos={msg['pos']}")

node = UDPNode(robot_id, on_msg)
while True:
    node.broadcast({"robot_id": robot_id, "pos": [0, 0], "ts": time.time()})
    time.sleep(0.5)

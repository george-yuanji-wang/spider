import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import sys, tty, termios

class KeyboardNode(Node):
    def __init__(self):
        super().__init__('keyboard')
        self.pub = self.create_publisher(String, 'motor/cmd', 10)
        self.get_logger().info('Keyboard node ready. WASD to drive, space to stop, q to quit')
        self.run()

    def get_key(self):
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            return sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

    def run(self):
        key_map = {
            'w' : '100, 100, 1',
            's' : '-100, -100, 1',
            'a' : '-50, 50, 1',
            'd' : '50, -50, 1',
            '' : '0, 0, 1',
        }
        while rclpy.ok():
            key = self.get_key()
            if key == 'q':
                break
            cmd = key_map.get(key, '0,0,0')
            msg = String()
            msg.data = cmd
            self.pub.publish(msg)
            self.get_logger().info(f'Key [{key}] -> {cmd}')
    
def main(args=None):
    rclpy.init(args=args)
    node = KeyboardNode()

if __name__ == '__name__':
    main()
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import serial
import serial.tools.list_ports

class MotorNode(Node):
    def __init__(self):
        super().__init__('motor')

        self.declare_parameter('serial_port', '/dev/ttyUSB0')
        self.declare_parameter('baud_rate', 115200)
        self.declare_parameter('retry_interval', 3.0)
        self.declare_parameter('handshake_ping', '-1,-1,0')
        self.declare_parameter('handshake_ack', 'gw')

        self.default_port = self.get_parameter('serial_port').value
        self.baud = self.get_parameter('baud_rate').value
        self.ping = self.get_parameter('handshake_ping').value + '\n'
        self.ack = self.get_parameter('handshake_ack').value
        retry = self.get_parameter('retry_interval').value

        self.ser = None
        self.create_subscription(String, 'motor/cmd', self.cb, 10)
        self.create_timer(retry, self.try_connect)
        self.get_logger().info('Motor node started')

    def try_handshake(self, device):
        try:
            s = serial.Serial(device, self.baud, timeout=1)
            s.write(self.ping.encode())
            response = s.readline().decode().strip()
            s.close()
            return response == self.ack
        except Exception:
            return False

    def find_port(self):
        if self.default_port and self.try_handshake(self.default_port):
            return self.default_port
        for p in serial.tools.list_ports.comports():
            if p.device == self.default_port:
                continue
            if self.try_handshake(p.device):
                return p.device
        return None

    def try_connect(self):
        if self.ser and self.ser.is_open:
            return
        port = self.find_port()
        if port is None: 
            self.get_logger().warn('No device found, retrying...')
            return
        try:
            self.ser = serial.Serial(port, self.baud, timeout=1)
            self.get_logger().info(f'Connected to {port}')
        except serial.SerialException as e:
            self.get_logger().error(f'Failed to open {port}: {e}')
            self.ser = None

    def cb(self, msg: String):
        if self.ser is None or not self.ser.is_open:
            self.get_logger().warn('Serial not connected, dropping command')
            return
        try:
            self.ser.write((msg.data.strip() + '\n').encode())
        except serial.SerialException as e:
            self.get_logger.error(f'Serial write failed: {e}')
            self.ser = None

def main(args=None):
    rclpy.init(args=args)
    node = MotorNode()
    rclpy.spin(node)

if __name__ == '__main__':
    main()
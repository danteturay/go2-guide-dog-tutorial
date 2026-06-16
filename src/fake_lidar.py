import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
import math

class FakeLidar(Node):
    def __init__(self, obstacle_distance=0.3):
        super().__init__('fake_lidar')
        self.publisher = self.create_publisher(LaserScan, '/scan', 10)
        self.timer = self.create_timer(0.1, self.publish_scan)
        self.obstacle_distance = obstacle_distance
        self.get_logger().info(f'Fake LiDAR publishing obstacle at {obstacle_distance}m')

    def publish_scan(self):
        msg = LaserScan()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'laser'
        msg.angle_min = -math.pi
        msg.angle_max = math.pi
        msg.angle_increment = math.pi / 180
        msg.range_min = 0.1
        msg.range_max = 10.0
        num_readings = 360
        msg.ranges = [self.obstacle_distance] * num_readings
        self.publisher.publish(msg)

def main():
    rclpy.init()
    node = FakeLidar(obstacle_distance=1.0)
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()

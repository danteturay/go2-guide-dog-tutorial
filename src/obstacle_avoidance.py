import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import Twist
from std_msgs.msg import String

# Distance thresholds
STOP_DISTANCE = 0.5      # Stop completely within 0.5m
SLOW_DISTANCE = 1.5      # Slow down within 1.5m
SLOW_SPEED_FACTOR = 0.3  # Reduce speed to 30% when slowing

class ObstacleAvoidanceNode(Node):
    def __init__(self):
        super().__init__('obstacle_avoidance')

        # Subscribe to LiDAR
        self.scan_subscriber = self.create_subscription(
            LaserScan,
            '/scan',
            self.scan_callback,
            10
        )

        # Subscribe to raw velocity commands
        self.cmd_subscriber = self.create_subscription(
            Twist,
            '/cmd_vel_raw',
            self.cmd_callback,
            10
        )

        # Subscribe to YOLO detections
        self.detection_subscriber = self.create_subscription(
            String,
            '/detections',
            self.detection_callback,
            10
        )

        # Publish safe velocity commands
        self.cmd_publisher = self.create_publisher(
            Twist,
            '/cmd_vel',
            10
        )

        # Publish status for voice feedback
        self.status_publisher = self.create_publisher(
            String,
            '/robot_status',
            10
        )

        self.latest_cmd = Twist()
        self.min_distance = float('inf')
        self.latest_detection = None

        self.get_logger().info('Obstacle avoidance node started')

    def detection_callback(self, msg):
        self.latest_detection = msg.data
        self.get_logger().info(f'YOLO detected: {msg.data}')

    def scan_callback(self, msg):
        # Get minimum distance from LiDAR
        valid_ranges = [r for r in msg.ranges if 0.1 < r < float('inf')]
        if not valid_ranges:
            return

        self.min_distance = min(valid_ranges)
        self.apply_safety(self.latest_cmd)

    def cmd_callback(self, msg):
        self.latest_cmd = msg
        self.apply_safety(msg)

    def apply_safety(self, cmd):
        safe_cmd = Twist()
        status = String()

        if self.min_distance < STOP_DISTANCE:
            # Stop completely
            # safe_cmd is already all zeros
            status.data = f'STOP: obstacle at {self.min_distance:.2f}m'
            if self.latest_detection:
                status.data += f' ({self.latest_detection})'
            self.get_logger().warn(status.data)

        elif self.min_distance < SLOW_DISTANCE:
            # Slow down
            safe_cmd.linear.x = cmd.linear.x * SLOW_SPEED_FACTOR
            safe_cmd.angular.z = cmd.angular.z
            status.data = f'SLOW: obstacle at {self.min_distance:.2f}m'
            if self.latest_detection:
                status.data += f' ({self.latest_detection})'
            self.get_logger().info(status.data)

        else:
            # Safe - forward command as-is
            safe_cmd = cmd
            status.data = 'CLEAR'

        self.cmd_publisher.publish(safe_cmd)
        self.status_publisher.publish(status)

def main():
    rclpy.init()
    node = ObstacleAvoidanceNode()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2
from geometry_msgs.msg import Twist
from std_msgs.msg import String
import struct
import math

STOP_DISTANCE = 1.0
SLOW_DISTANCE = 2.5
SLOW_SPEED_FACTOR = 0.3

MIN_HEIGHT = -0.1
MAX_HEIGHT = 1.5
FRONT_ANGLE = 60

class ObstacleAvoidanceNode(Node):
    def __init__(self):
        super().__init__('obstacle_avoidance')

        self.scan_subscriber = self.create_subscription(
            PointCloud2, '/velodyne_points', self.pointcloud_callback, 10
        )
        self.cmd_subscriber = self.create_subscription(
            Twist, '/cmd_vel_raw', self.cmd_callback, 10
        )
        self.detection_subscriber = self.create_subscription(
            String, '/detections', self.detection_callback, 10
        )
        self.cmd_publisher = self.create_publisher(Twist, '/cmd_vel', 10)
        self.status_publisher = self.create_publisher(String, '/robot_status', 10)

        self.latest_cmd = Twist()
        self.min_distance = float('inf')
        self.latest_detection = None

        # Cache field offsets per-message-layout so we don't re-parse the
        # fields list on every single point. Keyed by a layout fingerprint.
        self._offset_cache = {}

        self.get_logger().info('Obstacle avoidance node started (PointCloud2, dynamic field offsets)')

    def detection_callback(self, msg):
        self.latest_detection = msg.data

    def get_xyz_offsets(self, msg):
        """
        Read the actual field layout from the PointCloud2 message instead of
        assuming x/y/z always sit at bytes 0/4/8. Different LiDAR drivers
        (simulated Velodyne vs real Livox, etc.) can order or pad fields
        differently, so this makes the node portable between sim and the
        real robot without code changes.
        """
        # Build a fingerprint of the field layout so we only recompute when
        # it actually changes (e.g. switching sensors), not on every message.
        fingerprint = tuple((f.name, f.offset, f.datatype) for f in msg.fields)
        if fingerprint in self._offset_cache:
            return self._offset_cache[fingerprint]

        offsets = {}
        for field in msg.fields:
            if field.name in ('x', 'y', 'z'):
                offsets[field.name] = field.offset

        if not all(k in offsets for k in ('x', 'y', 'z')):
            self.get_logger().error(
                f'PointCloud2 message is missing x/y/z fields. '
                f'Found fields: {[f.name for f in msg.fields]}'
            )
            result = None
        else:
            result = (offsets['x'], offsets['y'], offsets['z'])

        self._offset_cache[fingerprint] = result
        return result

    def pointcloud_callback(self, msg):
        offsets = self.get_xyz_offsets(msg)
        if offsets is None:
            return  # can't safely parse this message, skip it

        x_off, y_off, z_off = offsets
        point_step = msg.point_step
        data = msg.data
        min_dist = float('inf')

        for i in range(msg.width * msg.height):
            base = i * point_step
            try:
                x = struct.unpack_from('f', data, base + x_off)[0]
                y = struct.unpack_from('f', data, base + y_off)[0]
                z = struct.unpack_from('f', data, base + z_off)[0]
            except struct.error:
                continue

            if not all(map(lambda v: -100 < v < 100, [x, y, z])):
                continue
            if z < MIN_HEIGHT or z > MAX_HEIGHT:
                continue

            angle = math.degrees(math.atan2(y, x))
            if abs(angle) > FRONT_ANGLE:
                continue

            dist = math.sqrt(x**2 + y**2)
            if dist < min_dist:
                min_dist = dist

        self.min_distance = min_dist
        self.apply_safety(self.latest_cmd)

    def cmd_callback(self, msg):
        self.latest_cmd = msg
        self.apply_safety(msg)

    def apply_safety(self, cmd):
        safe_cmd = Twist()
        status = String()

        if self.min_distance < STOP_DISTANCE:
            safe_cmd.linear.x = 0.0 if cmd.linear.x > 0 else cmd.linear.x
            safe_cmd.angular.z = cmd.angular.z

            status.data = f'STOP: obstacle at {self.min_distance:.2f}m'
            if self.latest_detection:
                status.data += f' ({self.latest_detection})'
            self.get_logger().warn(status.data)

        elif self.min_distance < SLOW_DISTANCE:
            safe_cmd.linear.x = cmd.linear.x * SLOW_SPEED_FACTOR if cmd.linear.x > 0 else cmd.linear.x
            safe_cmd.angular.z = cmd.angular.z

            status.data = f'SLOW: obstacle at {self.min_distance:.2f}m'
            if self.latest_detection:
                status.data += f' ({self.latest_detection})'
            self.get_logger().info(status.data)

        else:
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

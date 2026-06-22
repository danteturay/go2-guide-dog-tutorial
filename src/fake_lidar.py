import rclpy
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2, PointField
import struct
import math

class FakePointCloudLidar(Node):
    """
    Publishes a fake PointCloud2 message simulating a single obstacle directly
    ahead of the robot at a configurable distance. Used to test
    obstacle_avoidance.py without needing Gazebo running.
    """
    def __init__(self, obstacle_distance=2.0):
        super().__init__('fake_lidar')
        self.publisher = self.create_publisher(PointCloud2, '/velodyne_points', 10)
        self.timer = self.create_timer(0.1, self.publish_cloud)
        self.obstacle_distance = obstacle_distance
        self.get_logger().info(f'Fake PointCloud2 LiDAR publishing obstacle at {obstacle_distance}m')

    def publish_cloud(self):
        msg = PointCloud2()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'velodyne'

        # Define the field layout: x, y, z as float32, each 4 bytes,
        # matching the structure the real Velodyne/Livox drivers use.
        msg.fields = [
            PointField(name='x', offset=0, datatype=PointField.FLOAT32, count=1),
            PointField(name='y', offset=4, datatype=PointField.FLOAT32, count=1),
            PointField(name='z', offset=8, datatype=PointField.FLOAT32, count=1),
        ]
        msg.point_step = 12  # 3 floats * 4 bytes
        msg.is_bigendian = False
        msg.is_dense = True

        # Generate a flat "wall" of points directly ahead, at the configured
        # distance, spread across a few angles so the front-cone filter in
        # obstacle_avoidance.py has something to detect.
        points = []
        for angle_deg in range(-30, 31, 5):
            angle_rad = math.radians(angle_deg)
            x = self.obstacle_distance * math.cos(angle_rad)
            y = self.obstacle_distance * math.sin(angle_rad)
            z = 0.0  # at robot height, within MIN_HEIGHT/MAX_HEIGHT band
            points.append(struct.pack('fff', x, y, z))

        msg.height = 1
        msg.width = len(points)
        msg.row_step = msg.point_step * msg.width
        msg.data = b''.join(points)

        self.publisher.publish(msg)

def main():
    rclpy.init()
    # Change this value to test different zones:
    # > 2.5  -> CLEAR
    # 1.0-2.5 -> SLOW
    # < 1.0  -> STOP
    node = FakePointCloudLidar(obstacle_distance=2.0)
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()
    main()

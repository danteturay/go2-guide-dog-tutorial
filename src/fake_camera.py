import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
import cv2
import numpy as np

class FakeCamera(Node):
    def __init__(self):
        super().__init__('fake_camera')
        self.publisher = self.create_publisher(Image, '/camera/color/image_raw', 10)
        self.timer = self.create_timer(0.5, self.publish_image)
        
        # Load test image
        self.frame = cv2.imread('/workspace/go2-guide-dog-ros2/test_image.jpg')
        if self.frame is None:
            self.get_logger().error('Could not load test image')
        else:
            self.get_logger().info(f'Loaded test image: {self.frame.shape}')

    def publish_image(self):
        if self.frame is None:
            return
            
        msg = Image()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'camera'
        msg.height = self.frame.shape[0]
        msg.width = self.frame.shape[1]
        msg.encoding = 'bgr8'
        msg.step = self.frame.shape[1] * 3
        msg.data = self.frame.tobytes()
        self.publisher.publish(msg)

def main():
    rclpy.init()
    node = FakeCamera()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()
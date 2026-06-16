import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String
from cv_bridge import CvBridge
import cv2
from ultralytics import YOLO

# Objects that are high priority hazards for a blind user
HAZARD_CLASSES = ['person', 'car', 'truck', 'bicycle', 'motorcycle', 'bus', 'chair', 'dining table']

class YoloDetectorNode(Node):
    def __init__(self):
        super().__init__('yolo_detector')
        
        # Load YOLOv8 nano model (fastest, good enough for real-time)
        self.model = YOLO('/workspace/go2-guide-dog-ros2/yolov8n.pt')
        self.bridge = CvBridge()
        
        # Subscribe to camera topic
        self.image_subscriber = self.create_subscription(
            Image,
            '/camera/color/image_raw',
            self.image_callback,
            10
        )
        
        # Publish detected objects as a string topic
        self.detection_publisher = self.create_publisher(
            String,
            '/detections',
            10
        )
        
        self.get_logger().info('YOLO detector node started')

    def image_callback(self, msg):
        # Convert ROS image to OpenCV
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        
        # Run YOLO detection
        results = self.model(frame, verbose=False)
        
        detected_hazards = []
        
        for result in results:
            for box in result.boxes:
                class_name = self.model.names[int(box.cls)]
                confidence = float(box.conf)
                
                if class_name in HAZARD_CLASSES and confidence > 0.5:
                    detected_hazards.append(f'{class_name} ({confidence:.0%})')
                    self.get_logger().info(f'Detected: {class_name} confidence: {confidence:.0%}')
        
        # Publish detections
        if detected_hazards:
            msg_out = String()
            msg_out.data = ', '.join(detected_hazards)
            self.detection_publisher.publish(msg_out)

def main():
    rclpy.init()
    node = YoloDetectorNode()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()
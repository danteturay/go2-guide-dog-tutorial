import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import subprocess
import threading

class VoiceFeedbackNode(Node):
    def __init__(self):
        super().__init__('voice_feedback')
        
        # Subscribe to robot status
        self.status_subscriber = self.create_subscription(
            String,
            '/robot_status',
            self.status_callback,
            10
        )
        
        self.last_spoken = ''
        self.speaking = False
        
        self.get_logger().info('Voice feedback node started')

    def status_callback(self, msg):
        status = msg.data
        
        # Only speak if status has changed to avoid repeating constantly
        if status == self.last_spoken:
            return
            
        self.last_spoken = status
        
        # Convert status to natural language
        if status.startswith('STOP'):
            text = f'Warning, obstacle detected. Stopping.'
            if '(' in status:
                # Extract object name e.g. "STOP: obstacle at 0.3m (person)"
                obj = status.split('(')[1].split(')')[0]
                text = f'Warning, {obj} detected ahead. Stopping.'
        elif status.startswith('SLOW'):
            text = 'Obstacle nearby, slowing down.'
        else:
            text = ''  # Don't announce CLEAR every time
            
        if text:
            self.get_logger().info(f'Speaking: {text}')
            self.speak(text)

    def speak(self, text):
        # Run espeak in a separate thread so it doesn't block ROS2
        def _speak():
            try:
                subprocess.run(['espeak', text], 
                             capture_output=True, timeout=5)
            except Exception as e:
                self.get_logger().warn(f'Speech failed: {e}')
        
        thread = threading.Thread(target=_speak)
        thread.daemon = True
        thread.start()

def main():
    rclpy.init()
    node = VoiceFeedbackNode()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()
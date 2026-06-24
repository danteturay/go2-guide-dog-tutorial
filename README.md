# Go2 Guide Dog - ROS2

A ROS2-based software stack that turns the Unitree Go2 robot dog into a guide dog assistant for blind and visually impaired users.

Built during a research internship at the University of Southampton, supervised by Dr Mohammad Soorati.

---

## What This Project Does

- **Obstacle avoidance** - automatically slows or stops the robot when something is in its path, using LiDAR
- **Object detection** - uses YOLOv8 to identify what an obstacle is (person, car, bicycle, etc.)
- **Voice feedback** - the robot announces hazards out loud ("Warning, person detected ahead. Stopping.")
- **Voice commands** - control the robot by speaking ("go forward", "stop", "turn left")

### How the pieces fit together

```
[Microphone] → voice_commands.py ──→ /cmd_vel_raw ─────┐
                                                          ├─→ obstacle_avoidance.py ──→ /cmd_vel ──→ [Go2]
[LiDAR]      ───────────────────→ /velodyne_points ──────┘            │
[Camera]     ───────────────────→ /camera/image_raw → yolo_detector.py → /detections
                                                                        │
                                                            voice_feedback.py → [Speaker]
```

A movement command (from voice or keyboard) goes through a safety filter before it ever reaches the robot. The filter checks the LiDAR and, if YOLO has identified something, what that something is. If it's safe, the command passes through unchanged. If something is close, it slows down or gets blocked. A voice node announces what's happening throughout.

---

## Requirements

- **Ubuntu 22.04** - native, VM, or WSL2. This must be 22.04 specifically; ROS2 Humble (which this project depends on) does not support newer Ubuntu releases.
- If you don't have Ubuntu 22.04 available, see [Appendix A: Setting up a VM](#appendix-a-setting-up-a-vm).

---

## Quick Start

### 1. Run the setup script

This installs ROS2 Humble, Gazebo, and all dependencies in one go.

```bash
git clone https://github.com/danteturay/go2-guide-dog-ros2.git
cd go2-guide-dog-ros2
chmod +x setup.sh
./setup.sh
```

This takes 10–20 minutes, depending on your machine. Once it finishes, open a **new terminal** (so the environment changes take effect).

### 2. Build the Go2 simulation workspace

```bash
mkdir -p ~/go2_ws/src
cd ~/go2_ws/src
git clone https://github.com/anujjain-dev/unitree-go2-ros2.git
cd ~/go2_ws
sudo rosdep init      # only needed the very first time rosdep is used on this machine
rosdep update
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
echo "source ~/go2_ws/install/setup.bash" >> ~/.bashrc
source ~/.bashrc
```

### 3. Add the camera

The default robot model has a LiDAR but no camera. Add one:

```bash
nano ~/go2_ws/src/unitree-go2-ros2/robots/descriptions/go2_description/xacro/robot_VLP.xacro
```

Near the top, alongside the other `xacro:include` lines, add:
```xml
<xacro:include filename="$(find champ_description)/urdf/asus_camera.urdf.xacro"/>
```

Near the bottom, just before the closing `</robot>` tag, add:
```xml
<xacro:asus_camera name="camera" parent="trunk">
    <origin xyz="0.3 0 0.05" rpy="0 0 0"/>
</xacro:asus_camera>
```

Rebuild:
```bash
cd ~/go2_ws
colcon build --symlink-install
source install/setup.bash
```

### 4. Download the YOLO model (one-time)

```bash
python3 -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
```

### 5. Launch everything

Open **3 terminals**. In each one, run:
```bash
source /opt/ros/humble/setup.bash
source ~/go2_ws/install/setup.bash
```

Then, one command per terminal:

```bash
# Terminal 1 - The simulation
ros2 launch go2_config gazebo_velodyne.launch.py

# Terminal 2 - The safety and perception stack
# This starts obstacle avoidance, YOLO detection, and voice feedback.
# (Add 'use_voice_commands:=true' to the end of this command if you have a microphone)
cd ~/go2-guide-dog-ros2
ros2 launch guide_dog_launch.py

# Terminal 3 - Control the robot
# Use this to drive the robot via keyboard if you are not using voice commands.
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -r /cmd_vel:=/cmd_vel_raw
```

### 6. Try it out

1. In the Gazebo window, use the **Insert** tab on the left to add an obstacle in front of the robot.
   - `unit_box` works for testing LiDAR-only behaviour.
   - **YOLO will not reliably detect plain untextured shapes** - use the **`person_standing`** model to test object detection.
2. Drive the robot toward the obstacle (keyboard: `i` forward, `k` stop, `j`/`l` turn, or say "go forward").
3. Watch Terminal 2 - the status should move through:
   - `CLEAR` (more than ~2.5m away)
   - `SLOW: obstacle at 1.8m`
   - `STOP: obstacle at 0.9m (person (87%))`; including YOLO's identification, if available
4. You should hear the robot announce the obstacle once it enters the SLOW or STOP zone (once per transition, not continuously).
5. Try reversing or turning while stopped - both still work; only *forward* motion into the obstacle is blocked (and only forward speed is reduced in the SLOW zone).

If all of that works, you have a fully functioning simulated demo.

---

## Reference

### Safety Zones

| Distance to obstacle | Behaviour | Status |
|---|---|---|
| > 2.5m | Full speed | `CLEAR` |
| 1.0m – 2.5m | 30% speed (forward only) | `SLOW` |
| < 1.0m | Forward blocked (reverse/turn still allowed) | `STOP` |

### Voice Commands

| You say | Robot does |
|---|---|
| "go forward" | Moves forward at 0.5 m/s |
| "go forward slowly" | Moves forward at 0.2 m/s |
| "stop" / "halt" / "wait" | Stops |
| "turn left" / "turn right" | Rotates in place |
| "go back" | Moves backward |
| "faster" / "speed up" | Moves at 0.8 m/s |

### ROS2 Topics

| Topic | Type | Description |
|---|---|---|
| `/velodyne_points` | `sensor_msgs/PointCloud2` | 3D LiDAR data (simulation) |
| `/camera/image_raw` | `sensor_msgs/Image` | Camera feed (simulation) |
| `/cmd_vel_raw` | `geometry_msgs/Twist` | Unfiltered movement commands |
| `/cmd_vel` | `geometry_msgs/Twist` | Safety-filtered movement commands sent to the robot |
| `/detections` | `std_msgs/String` | Objects identified by YOLO |
| `/robot_status` | `std_msgs/String` | Current safety state (`CLEAR`/`SLOW`/`STOP`) |
| `/voice_text` | `std_msgs/String` | Last recognised speech |

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'rclpy'`**
You forgot to source ROS2 in this terminal: `source /opt/ros/humble/setup.bash`.

**`package 'X' not found` when launching the simulation**
Install it: `sudo apt install ros-humble-x` (replace `x` with the package name, swapping underscores for dashes). Different machines are sometimes missing different optional dependencies even after running `setup.sh`.

**No microphone detected**
Check it's connected at the OS level: `arecord -l`. If using a VM, ensure the sound card is enabled in VM settings with "Connect at power on" checked.

**YOLO never detects anything in simulation**
Plain Gazebo primitive shapes (boxes, spheres, cylinders) have no texture or realistic geometry, so YOLO won't recognise them as anything. Use a more realistic model like `person_standing` to test detection.

---

## Moving to the Real Robot

The real Go2 uses different topic names than the simulation:

| Data | Simulation Topic | Real Robot Topic |
|---|---|---|
| LiDAR | `/velodyne_points` | `/utlidar/cloud` |
| Camera | `/camera/image_raw` | `/camera/color/image_raw` |

Connect via Ethernet, configure CycloneDDS for your network interface (see the Unitree `unitree_ros2` SDK docs), then either remap topics at launch or update the topic names in `obstacle_avoidance.py` and `yolo_detector.py` directly.

---

## Appendix A: Setting up a VM

If you don't have an Ubuntu 22.04 machine available, a virtual machine works fine.

1. **Download Ubuntu 22.04 Desktop**: [releases.ubuntu.com/22.04](https://releases.ubuntu.com/22.04/) - get `ubuntu-22.04.x-desktop-amd64.iso`.
2. **Create the VM** (VMware Workstation or VirtualBox, both free):
   - RAM: at least 8GB, ideally 12GB+
   - CPU cores: at least 4
   - Disk: at least 50GB
   - Enable **"Accelerate 3D graphics"** in display settings
3. Install Ubuntu with the standard installer.
4. Enable clipboard sharing between host and VM:
   ```bash
   sudo apt install open-vm-tools open-vm-tools-desktop -y
   sudo reboot
   ```

Then continue from [Quick Start](#quick-start) above.

---

## Appendix B: Testing Without the Simulation

If you want to test the node logic without Gazebo running at all, use the fake sensor publishers. This is useful for quick iteration on the obstacle avoidance / YOLO logic itself, separate from the simulation environment.

**Obstacle avoidance, using fake LiDAR data:**
```bash
# Terminal 1
python3 src/obstacle_avoidance.py

# Terminal 2 - fake LiDAR (edit obstacle_distance in main() to test different zones)
python3 src/fake_lidar.py

# Terminal 3 - send a movement command
ros2 topic pub /cmd_vel_raw geometry_msgs/msg/Twist "{linear: {x: 0.5}}" --rate 10

# Terminal 4 - watch the result
ros2 topic echo /robot_status
```

**YOLO, using a static test image:**
```bash
python3 src/fake_camera.py
python3 src/yolo_detector.py
ros2 topic echo /detections
```

---

## Authors

Dante Turay - University of Southampton, 2026
Supervised by Dr Mohammad Soorati

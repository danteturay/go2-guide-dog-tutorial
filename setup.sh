#!/bin/bash
# Go2 Guide Dog - one-time environment setup
# Run this once on a fresh Ubuntu 22.04 machine (native, VM, or WSL2).

set -e  # stop on first error

echo "=== Updating system ==="
sudo apt update && sudo apt upgrade -y

echo "=== Adding general tools ==="
sudo apt install git -y

echo "=== Adding ROS2 package repository ==="
sudo apt install curl software-properties-common -y
sudo add-apt-repository universe -y
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu jammy main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null
sudo apt update

echo "=== Installing ROS2 Humble ==="
sudo apt install ros-humble-desktop -y

echo "=== Checking system architecture ==="
ARCH=$(dpkg --print-architecture)
if [ "$ARCH" != "amd64" ]; then
    echo ""
    echo "!!! This script targets amd64 (standard Intel/AMD machines and VMs)."
    echo "!!! Detected architecture: $ARCH"
    echo "!!! Gazebo Classic's ROS2 bridge packages (gazebo-ros-pkgs) are only"
    echo "!!! published for amd64 - they are not available on arm64 (e.g. Apple"
    echo "!!! Silicon Macs, Raspberry Pi, ARM laptops) and this script will fail"
    echo "!!! partway through if you continue on this machine."
    echo "!!!"
    echo "!!! If you're on an ARM machine, run this inside an amd64 VM instead"
    echo "!!! (e.g. VMware/VirtualBox/UTM configured to emulate x86_64), or use"
    echo "!!! a native amd64 Ubuntu machine."
    read -p "Continue anyway? (not recommended) [y/N] " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "=== Installing Gazebo Classic and core tools ==="
sudo apt install ros-humble-gazebo-ros-pkgs python3-colcon-common-extensions -y

echo "=== Installing Go2 simulation dependencies ==="
sudo apt install ros-humble-gazebo-ros2-control ros-humble-xacro \
    ros-humble-robot-localization ros-humble-ros2-controllers \
    ros-humble-ros2-control ros-humble-velodyne \
    ros-humble-velodyne-gazebo-plugins ros-humble-velodyne-description \
    ros-humble-controller-manager ros-humble-twist-mux \
    ros-humble-nav2-bringup ros-humble-navigation2 \
    ros-humble-teleop-twist-keyboard -y

echo "=== Installing this project's dependencies ==="
sudo apt install portaudio19-dev espeak python3-pip python3-rosdep -y
pip3 install ultralytics SpeechRecognition pyaudio
pip3 install "numpy<2"

echo "=== Setting up ROS2 environment in ~/.bashrc ==="
grep -qxF "source /opt/ros/humble/setup.bash" ~/.bashrc || echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc

echo ""
echo "=== Base setup complete ==="
echo "Next: clone and build the Go2 simulation workspace (see README Part 2)."

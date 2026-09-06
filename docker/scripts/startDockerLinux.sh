#! /bin/bash
xhost +local:docker

# Build first from the class workspace:
# docker compose -f docker/compose.yaml build

# Mount the class ROS workspace next to this script, so the command works
# regardless of where the class folder is located on the host.
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
LOCAL_DIR="$(CDPATH= cd -- "$SCRIPT_DIR/../../ros_ws" && pwd)"


docker run -it -v /tmp/.X11-unix:/tmp/.X11-unix \
  -v "${LOCAL_DIR}":/home/ros/ros_ws \
  -w /home/ros/ros_ws \
  -e DISPLAY \
  -e WAYLAND_DISPLAY \
  -e XDG_RUNTIME_DIR=/run/user/$(id -u) \
  -e PULSE_SERVER=unix:${XDG_RUNTIME_DIR}/pulse/native \
  -v /run/user/$(id -u):/run/user/$(id -u) \
  --device /dev/dri \
  --group-add video \
  intro-to-robotics-ros:humble

xhost -local:docker

# ROS 2 Class Workspace

This is the mounted colcon workspace for Intro to Robotics. Put ROS 2 packages
under `src/`, build from `/home/ros/ros_ws` inside the container, and keep
generated files in `build/`, `install/`, and `log/`.

```bash
colcon build --symlink-install
source install/setup.bash
```

Homework belongs in `src/homework/`; lab packages belong in `src/labs/`.
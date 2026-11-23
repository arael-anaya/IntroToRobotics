# Intro to Robotics (MEGN 441)

The repo root is the colcon workspace. Docker mounts it at `/home/ros/ros_ws`.

```
docker/     Dockerfile, compose.yaml, start scripts, install guide
homework/   Hw0, Hw1, Hw2, ...
labs/       megn441 lab repo (git submodule)
tools/      shared helper packages (wasd_teleop)
```

Build inside the container:

```bash
cd /home/ros/ros_ws
colcon build --symlink-install
source install/setup.bash
```

colcon finds packages recursively, so anything under `homework/`, `labs/`, or
`tools/` gets built. `build/`, `install/`, and `log/` land at the repo root and
are git-ignored.

#!/usr/bin/env python3
"""WASD keyboard teleop. Publishes geometry_msgs/Twist on a configurable topic.

Hold a key to drive; release and the robot decelerates to a stop.

  ros2 run wasd_teleop wasd                                  # /cmd_vel
  ros2 run wasd_teleop wasd --ros-args -p topic:=turtle1/cmd_vel
"""
import select
import sys
import termios
import time
import tty

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node

HELP = """
WASD teleop  (publishing to {topic})
---------------------------------
   q  w  e        w/s : forward / back
   a  s  d        a/d : turn left / right
                  q/e : forward + turn left / right
   space or x : emergency stop (no ramp)
   r / f      : linear speed  +10% / -10%
   t / g      : angular speed +10% / -10%
   Ctrl-C     : quit (robot is stopped)

Hold keys to drive. Release and the robot slows to a stop.
"""

# key -> (linear sign, angular sign)
MOVES = {
    'w': (1, 0), 's': (-1, 0), 'a': (0, 1), 'd': (0, -1),
    'q': (1, 1), 'e': (1, -1),
}


def approach(cur, target, step):
    if cur < target:
        return min(cur + step, target)
    return max(cur - step, target)


class WasdTeleop(Node):
    def __init__(self):
        super().__init__('wasd_teleop')
        self.declare_parameter('topic', 'cmd_vel')
        self.declare_parameter('linear', 5.0)         # max m/s
        self.declare_parameter('angular', 6.0)        # max rad/s
        self.declare_parameter('linear_accel', 10.0)  # m/s^2 speeding up
        self.declare_parameter('angular_accel', 15.0) # rad/s^2 speeding up
        self.declare_parameter('decel_factor', 1.0)   # >1 stops faster than it starts
        # Terminals send nothing between the first keypress and key-repeat
        # (~0.5 s by default), so a key counts as "held" for this long.
        self.declare_parameter('hold_timeout', 0.55)
        p = lambda n: float(self.get_parameter(n).value)
        self.topic = self.get_parameter('topic').value
        self.linear, self.angular = p('linear'), p('angular')
        self.lin_acc, self.ang_acc = p('linear_accel'), p('angular_accel')
        self.decel = p('decel_factor')
        self.hold_timeout = p('hold_timeout')

        self.pub = self.create_publisher(Twist, self.topic, 10)
        self.sign = (0, 0)
        self.last_key = 0.0
        self.v = 0.0
        self.w = 0.0
        self.dt = 0.05
        self.create_timer(self.dt, self.step)

    def step(self):
        held = (time.monotonic() - self.last_key) < self.hold_timeout
        sl, sa = self.sign if held else (0, 0)
        tv, tw = sl * self.linear, sa * self.angular
        # Slowing toward a smaller magnitude uses the (possibly larger) decel rate.
        lin_rate = self.lin_acc * (self.decel if abs(tv) < abs(self.v) else 1.0)
        ang_rate = self.ang_acc * (self.decel if abs(tw) < abs(self.w) else 1.0)
        self.v = approach(self.v, tv, lin_rate * self.dt)
        self.w = approach(self.w, tw, ang_rate * self.dt)
        msg = Twist()
        msg.linear.x = self.v
        msg.angular.z = self.w
        self.pub.publish(msg)
        print(f'\rv={self.v:+.2f} m/s  w={self.w:+.2f} rad/s  '
              f'(max {self.linear:.2f}/{self.angular:.2f})   ', end='', flush=True)

    def on_key(self, key):
        if key in MOVES:
            self.sign = MOVES[key]
            self.last_key = time.monotonic()
        elif key in (' ', 'x'):
            self.sign = (0, 0)
            self.v = self.w = 0.0
        elif key == 'r':
            self.linear *= 1.1
        elif key == 'f':
            self.linear /= 1.1
        elif key == 't':
            self.angular *= 1.1
        elif key == 'g':
            self.angular /= 1.1


def main():
    if not sys.stdin.isatty():
        sys.exit('wasd needs an interactive terminal (use `ros2 run`, not a background process).')
    rclpy.init()
    node = WasdTeleop()
    settings = termios.tcgetattr(sys.stdin)
    print(HELP.format(topic=node.topic))
    try:
        tty.setcbreak(sys.stdin.fileno())
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.01)
            while select.select([sys.stdin], [], [], 0)[0]:
                node.on_key(sys.stdin.read(1).lower())
    except KeyboardInterrupt:
        pass
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
        node.v = node.w = 0.0
        node.pub.publish(Twist())
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        print('\nstopped.')


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Draws a black bar on the ground behind the robot so you can see where it has travelled."""
import math
import os
import pty
import queue
import shutil
import subprocess
import sys
import threading
import time

MODEL = sys.argv[1] if len(sys.argv) > 1 else 'demo_bot'
WORLD = sys.argv[2] if len(sys.argv) > 2 else None  # auto-detected if omitted
STEP = 0.2      # metres of travel between bar segments
WIDTH = 0.08    # bar width (m)
HEIGHT = 0.01   # bar thickness (m)

CLI, MSGS = ('gz', 'gz.msgs') if shutil.which('gz') else ('ign', 'ignition.msgs')

marker_id = 0


def die_with_parent():
    # Kill the child 'ign topic' when this script dies, so it can't outlive the launch
    import ctypes
    ctypes.CDLL('libc.so.6').prctl(1, 15)  # PR_SET_PDEATHSIG, SIGTERM


def add_segment(a, b):
    global marker_id
    marker_id += 1
    length = math.hypot(b[0] - a[0], b[1] - a[1]) + WIDTH  # overlap so corners join
    yaw = math.atan2(b[1] - a[1], b[0] - a[0])
    req = (
        'action: ADD_MODIFY, ns: "trail", id: %d, type: BOX, '
        'material {ambient {r:0 g:0 b:0 a:1} diffuse {r:0 g:0 b:0 a:1}}, '
        'scale {x: %f, y: %f, z: %f}, '
        'pose {position {x: %f, y: %f, z: %f} orientation {z: %f, w: %f}}'
        % (marker_id, length, WIDTH, HEIGHT,
           (a[0] + b[0]) / 2, (a[1] + b[1]) / 2, HEIGHT / 2 + 0.002,
           math.sin(yaw / 2), math.cos(yaw / 2)))
    # The /marker service's real reply type is Empty, not Boolean; requesting the
    # wrong reptype makes ign-transport drop the request before it ever draws anything.
    subprocess.run([CLI, 'service', '-s', '/marker', '--reqtype', MSGS + '.Marker',
                    '--reptype', MSGS + '.Empty', '--timeout', '500', '--req', req],
                   capture_output=True)


def draw_worker(segments):
    # Each 'ign service' call spawns a whole new process, which is slow to start.
    # Doing that on the same thread that reads poses lets the OS pipe buffer fill
    # up while we wait, so poses get dropped and the trail lags/stutters. Drawing
    # happens here instead, one segment at a time, off that critical path.
    while True:
        add_segment(*segments.get())


def poses(stream):
    """Yield (name, x, y) for every top-level pose in the pose/info text stream."""
    depth = 0
    cur = None
    section = None
    for raw in stream:
        line = raw.strip()
        if line.endswith('{'):
            depth += 1
            if depth == 1 and line.startswith('pose'):
                cur = {'name': '', 'x': 0.0, 'y': 0.0}
            elif depth == 2:
                section = line.split()[0]
        elif line == '}':
            if depth == 1 and cur is not None:
                yield cur['name'], cur['x'], cur['y']
                cur = None
            depth -= 1
        elif cur is not None:
            key, _, val = line.partition(':')
            if depth == 1 and key == 'name':
                cur['name'] = val.strip().strip('"')
            elif depth == 2 and section == 'position' and key in ('x', 'y'):
                cur[key] = float(val)


def find_world():
    # Wait for the sim to come up, then read the world name from the topic list
    while True:
        out = subprocess.run([CLI, 'topic', '-l'], capture_output=True, text=True).stdout
        for line in out.splitlines():
            parts = line.strip().split('/')
            if line.strip().endswith('/pose/info') and len(parts) > 3 and parts[1] == 'world':
                return parts[2]
        time.sleep(1)


def main():
    world = WORLD or find_world()
    cmd = [CLI, 'topic', '-e', '-t', '/world/%s/dynamic_pose/info' % world]
    # A pty makes ign line-buffer its output; through a plain pipe it is block-buffered
    master, slave = pty.openpty()
    subprocess.Popen(cmd, stdout=slave, stderr=subprocess.DEVNULL, preexec_fn=die_with_parent)
    os.close(slave)
    stream = os.fdopen(master, "r", errors="replace")

    segments = queue.Queue()
    threading.Thread(target=draw_worker, args=(segments,), daemon=True).start()

    last = None
    for name, x, y in poses(stream):
        if name != MODEL:
            continue
        if last is None:
            last = (x, y)
        elif math.hypot(x - last[0], y - last[1]) >= STEP:
            segments.put((last, (x, y)))
            last = (x, y)


if __name__ == '__main__':
    main()

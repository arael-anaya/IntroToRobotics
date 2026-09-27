#!/usr/bin/env python3
"""Third-person chase camera for Gazebo. Press K in the sim window to toggle free camera."""
import subprocess
import threading
import time

import shutil
import sys
MODEL = sys.argv[1] if len(sys.argv) > 1 else 'demo_bot'
OFFSET = 'x: -3, y: 0, z: 1.5'
K_KEY = 75  # Qt::Key_K

# Ignition Fortress ships 'ign' with ignition.msgs; newer Gazebo ships 'gz' with gz.msgs
CLI, MSGS = ('gz', 'gz.msgs') if shutil.which('gz') else ('ign', 'ignition.msgs')

following = True


def die_with_parent():
    # Kill the child 'ign topic' when this script dies, so it can't outlive the launch
    import ctypes
    ctypes.CDLL('libc.so.6').prctl(1, 15)  # PR_SET_PDEATHSIG, SIGTERM


def gz_service(service, reqtype, req):
    subprocess.run([CLI, 'service', '-s', service, '--reqtype', reqtype,
                    '--reptype', MSGS + '.Boolean', '--timeout', '2000',
                    '--req', req], capture_output=True)


def set_follow(on):
    if on:
        gz_service('/gui/follow/offset', MSGS + '.Vector3d', OFFSET)
    gz_service('/gui/follow', MSGS + '.StringMsg',
               'data: "%s"' % (MODEL if on else ''))


def start_when_robot_exists():
    # The robot is spawned after the GUI starts. Wait for it, then send the
    # follow request once. Re-sending repeatedly would reset the camera and
    # fight the user's zoom.
    while True:
        out = subprocess.run([CLI, 'model', '--list'], capture_output=True,
                             text=True).stdout
        if MODEL in out:
            break
        time.sleep(1)
    time.sleep(1)
    if following:
        set_follow(True)


def main():
    global following
    threading.Thread(target=start_when_robot_exists, daemon=True).start()
    p = subprocess.Popen([CLI, 'topic', '-e', '-t', '/keyboard/keypress'],
                         stdout=subprocess.PIPE, text=True, preexec_fn=die_with_parent)
    for line in p.stdout:
        if line.strip() == 'data: %d' % K_KEY:
            following = not following
            set_follow(following)


if __name__ == '__main__':
    main()

import rclpy
from rclpy.node import Node
from turtlesim.msg import Pose
from geometry_msgs.msg import Twist , Point

import numpy as np
# ros2 topic pub /turtle1/goal_pose geometry_msgs/msg/Point "{x: 5.5, y: 5.5, z: 0.0}" --once


class turtleController(Node):
    def __init__(self):
        self.goalX = 5.5
        self.goalY = 5.5

        super().__init__("turtle_controller")
        self.publisher_ = self.create_publisher(Twist, 'turtle1/cmd_vel' , 10)
        self.poseSubscription = self.create_subscription(
            Pose, 'turtle1/pose' , self.poseCallback, 10)
        self.goalSubscription = self.create_subscription(
                    Point, 'turtle1/goal_pose' , self.goalCallback, 10)

    def goalCallback(self,msg):
        self.goalX = msg.x
        self.goalY = msg.y

    def poseCallback(self, msg):
        currX = msg.x
        currY = msg.y
        goalX = self.goalX
        goalY = self.goalY

        currTheta   = msg.theta
        speedCMD = Twist()

        diffY = goalY - currY
        diffX =  goalX - currX

        if diffX**2 + diffY**2 < 0.01:
            self.publisher_.publish(speedCMD)
            return

        goalTheta = np.arctan2( diffY , diffX)
        angleDiff = goalTheta - currTheta
        angleDiff = np.arctan2(np.sin(angleDiff) , np.cos(angleDiff))

        Kpt = 2.0
        Kpv = 2.0

        omegaZ = Kpt * angleDiff
        vX = Kpv * np.sqrt((diffX)**2 + (diffY)**2)

        speedCMD.linear.x = vX
        speedCMD.angular.z = omegaZ

        self.publisher_.publish(speedCMD)

        return


def main(args=None):
    rclpy.init(args=args)
    node = turtleController()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
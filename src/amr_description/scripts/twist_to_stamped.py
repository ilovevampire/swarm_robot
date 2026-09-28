#!/usr/bin/env python3
"""
twist_to_stamped.py
====================
Minimal replacement for the `twist_stamper` package (used here because
apt couldn't reach packages.ros.org). Subscribes plain geometry_msgs/Twist
on /cmd_vel, republishes as geometry_msgs/TwistStamped with a current
timestamp on /diff_drive_controller/cmd_vel - this installed version of
diff_drive_controller requires TwistStamped regardless of the
use_stamped_vel setting (confirmed via `ros2 topic info -v` and the
official Jazzy docs).
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, TwistStamped


class TwistToStamped(Node):

    def __init__(self):
        super().__init__("twist_to_stamped")

        self.declare_parameter("frame_id", "")
        self.frame_id = self.get_parameter("frame_id").value

        self.pub = self.create_publisher(
            TwistStamped, "/diff_drive_controller/cmd_vel", 10
        )
        self.create_subscription(Twist, "/cmd_vel", self._on_twist, 10)

    def _on_twist(self, msg: Twist):
        stamped = TwistStamped()
        stamped.header.stamp = self.get_clock().now().to_msg()
        stamped.header.frame_id = self.frame_id
        stamped.twist = msg
        self.pub.publish(stamped)


def main():
    rclpy.init()
    node = TwistToStamped()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
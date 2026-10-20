import argparse
import math
import time
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseWithCovarianceStamped

parser = argparse.ArgumentParser()
parser.add_argument('--x',type=float,required=True)
parser.add_argument('--y',type=float,required=True)
parser.add_argument('--yaw',type=float,required=True)
args = parser.parse_args()
rclpy.init(); node = Node('set_verified_initial_pose',parameter_overrides=[rclpy.parameter.Parameter('use_sim_time',value=True)])
publisher = node.create_publisher(PoseWithCovarianceStamped,'/initialpose',10)
end = time.monotonic()+15
while time.monotonic()<end and (publisher.get_subscription_count()==0 or node.get_clock().now().nanoseconds==0):
    rclpy.spin_once(node,timeout_sec=.1)
if not publisher.get_subscription_count() or not node.get_clock().now().nanoseconds:
    raise RuntimeError('AMCL subscriber or /clock unavailable')
msg = PoseWithCovarianceStamped(); msg.header.frame_id='map'; msg.header.stamp=node.get_clock().now().to_msg()
msg.pose.pose.position.x=args.x; msg.pose.pose.position.y=args.y
msg.pose.pose.orientation.z=math.sin(args.yaw/2);msg.pose.pose.orientation.w=math.cos(args.yaw/2)
msg.pose.covariance[0]=.25; msg.pose.covariance[7]=.25;msg.pose.covariance[35]=.0685
publisher.publish(msg)
for _ in range(10):rclpy.spin_once(node,timeout_sec=.1)
node.destroy_node(); rclpy.shutdown()

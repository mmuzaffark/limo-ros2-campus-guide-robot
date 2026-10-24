#!/usr/bin/env python3
import math, rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from nav_msgs.msg import Odometry
from gazebo_msgs.msg import ModelStates
rclpy.init()
n = Node('odo_chk', parameter_overrides=[Parameter('use_sim_time', Parameter.Type.BOOL, True)])
d = {}
yaw = lambda q: math.degrees(math.atan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z)))
n.create_subscription(Odometry, '/odom', lambda m: d.update(o=(m.pose.pose.position.x, m.pose.pose.position.y, yaw(m.pose.pose.orientation))), 10)
def ms(m):
    i = next(k for k, s in enumerate(m.name) if 'limo' in s); p = m.pose[i]
    d['g'] = (p.position.x, p.position.y, yaw(p.orientation))
n.create_subscription(ModelStates, '/gazebo/model_states', ms, 10)
while 'o' not in d or 'g' not in d: rclpy.spin_once(n, timeout_sec=0.2)
o, g = d['o'], d['g']
print('odom   x=%+.3f y=%+.3f yaw=%+.1f' % o)
print('gazebo x=%+.3f y=%+.3f yaw=%+.1f' % g)

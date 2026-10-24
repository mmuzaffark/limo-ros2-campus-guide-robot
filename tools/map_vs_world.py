#!/usr/bin/env python3
import math, time, rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.time import Time
from gazebo_msgs.msg import ModelStates
from tf2_ros import Buffer, TransformListener

def yaw(q): return math.atan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z))
rclpy.init()
n = Node('map_vs_world', parameter_overrides=[Parameter('use_sim_time', Parameter.Type.BOOL, True)])
buf = Buffer(); TransformListener(buf, n)
ms = {}
n.create_subscription(ModelStates, '/gazebo/model_states', lambda m: ms.update(m=m), 10)
t0 = time.time(); tf = None
while time.time() - t0 < 8:
    rclpy.spin_once(n, timeout_sec=0.1)
    if 'm' in ms and buf.can_transform('map', 'base_link', Time()):
        tf = buf.lookup_transform('map', 'base_link', Time()); break
if tf is None: raise SystemExit('no tf map->base_link or /gazebo/model_states')
m = ms['m']; i = next(k for k, nm in enumerate(m.name) if 'limo' in nm); w = m.pose[i]
mx, my, my_ = tf.transform.translation.x, tf.transform.translation.y, yaw(tf.transform.rotation)
wx, wy, wy_ = w.position.x, w.position.y, yaw(w.orientation)
d = math.degrees(math.atan2(math.sin(my_-wy_), math.cos(my_-wy_)))
print(f'world x={wx:+.3f} y={wy:+.3f} yaw={math.degrees(wy_):+.1f}')
print(f'map   x={mx:+.3f} y={my:+.3f} yaw={math.degrees(my_):+.1f}')
print(f'diff  dx={mx-wx:+.3f} dy={my-wy:+.3f} dyaw={d:+.1f} deg')

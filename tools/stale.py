import rclpy, time
from rclpy.qos import qos_profile_sensor_data
from geometry_msgs.msg import PolygonStamped
from rosgraph_msgs.msg import Clock
rclpy.init(); n = rclpy.create_node('stale_check'); fp = {}; c = [None]
for k in ('global_costmap', 'local_costmap'):
    n.create_subscription(PolygonStamped, f'/{k}/published_footprint',
        lambda m, k=k: fp.__setitem__(k, m.header.stamp.sec + m.header.stamp.nanosec * 1e-9), 10)
n.create_subscription(Clock, '/clock', lambda m: c.__setitem__(0, m.clock.sec + m.clock.nanosec * 1e-9), qos_profile_sensor_data)
t0 = time.time()
while (len(fp) < 2 or c[0] is None) and time.time() - t0 < 8: rclpy.spin_once(n, timeout_sec=0.2)
lag = {k: (c[0] - fp[k]) if (k in fp and c[0] is not None) else None for k in ('global_costmap', 'local_costmap')}
txt = ' '.join(f"{k.split('_')[0]}-lag {'NONE' if v is None else '%.1fs' % v}" for k, v in lag.items())
print(txt + (' FROZEN' if any(v is None or v > 5 for v in lag.values()) else ''))

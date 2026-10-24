import math, re, subprocess, os
o = subprocess.run("timeout 6 ros2 run tf2_ros tf2_echo map base_link", shell=True, capture_output=True, text=True).stdout
x, y = map(float, re.search(r"Translation: \[([-\d.]+), ([-\d.]+)", o).groups())
yaw = float(re.search(r"RPY \(radian\) \[[-\d.]+, [-\d.]+, ([-\d.]+)\]", o).group(1))
print(f"robot map pose: x={x:.3f} y={y:.3f} yaw={yaw:.3f}")
for n, l in enumerate(open(os.path.expanduser('~/limo_ws/params/goals.txt')), 1):
    p = l.split()
    if len(p) < 4: continue
    gx, gy, gz, gw = map(float, p[:4])
    dy = (2*math.atan2(gz, gw) - yaw + math.pi) % (2*math.pi) - math.pi
    print(f"goal {n}: dist={math.hypot(gx-x, gy-y):.3f} m  yaw_err={dy:+.3f} rad")

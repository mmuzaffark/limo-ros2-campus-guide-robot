import subprocess, re, sys
def run(c): return subprocess.run(c, shell=True, capture_output=True, text=True, executable='/bin/bash').stdout
def xy(s): return [float(v) for v in re.findall(r'[xy]:\s*([-\d.e]+)', s)[:2]]
ms = run("timeout 8 ros2 topic echo /gazebo/model_states --once")
names = [n[2:].strip() for n in re.search(r'name:\s*\n((?:- .*\n)+)', ms).group(1).splitlines()]
t = [float(v) for v in re.findall(r'position:\s*\n\s*x:\s*([-\d.e]+)\s*\n\s*y:\s*([-\d.e]+)', ms)[names.index('limo_gazebo')]]
a = xy(run("timeout 6 ros2 topic echo /amcl_pose --once --qos-durability transient_local --qos-reliability reliable --field pose.pose.position"))
d = lambda p, q: ((p[0]-q[0])**2 + (p[1]-q[1])**2) ** 0.5
line = 'truth %s | amcl %s | amcl error %.3f m' % ([round(v,3) for v in t], [round(v,3) for v in a], d(a,t))
if len(sys.argv) == 3: line += ' | parking error %.3f m' % d(t, [float(sys.argv[1]), float(sys.argv[2])])
print(line)

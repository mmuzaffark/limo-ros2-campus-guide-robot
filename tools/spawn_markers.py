#!/usr/bin/env python3
import os, subprocess, sys
dx, dy = (float(sys.argv[1]), float(sys.argv[2])) if len(sys.argv) > 2 else (0.0, 0.0)
W, H, T = 0.09, 0.16, 0.02
SEG = {'a': (0, H/2-T/2, W, T), 'd': (0, -H/2+T/2, W, T), 'g': (0, 0, W, T),
       'f': (-W/2+T/2, H/4, T, H/2), 'b': (W/2-T/2, H/4, T, H/2),
       'e': (-W/2+T/2, -H/4, T, H/2), 'c': (W/2-T/2, -H/4, T, H/2)}
DIG = {'1': 'bc', '2': 'abged', '3': 'abgcd', '4': 'fgbc', '5': 'afgcd', 'H': 'febcg'}
def box(n, u, v, su, sv, z, sz, col):
    return (f'<visual name="{n}"><cast_shadows>false</cast_shadows><pose>{v} {-u} {z} 0 0 0</pose>'
            f'<geometry><box><size>{sv} {su} {sz}</size></box></geometry>'
            f'<material><ambient>{col}</ambient><diffuse>{col}</diffuse></material></visual>')
goals = [l.split() for l in open(os.path.expanduser('~/limo_ws/params/goals.txt')) if l.strip()]
for i, g in enumerate(goals):
    label = 'H' if i == len(goals)-1 else str(i+1); name = f'goal_{label}'
    x, y = float(g[0])-dx, float(g[1])-dy
    vis = box('plate', 0, 0, 0.22, 0.22, 0.001, 0.002, '1 0.85 0 1')
    for k, s in enumerate(DIG[label]):
        u, v, su, sv = SEG[s]; vis += box(f's{k}', u, v, su, sv, 0.003, 0.002, '0 0 0 1')
    path = f'/tmp/{name}.sdf'
    open(path, 'w').write(f'<sdf version="1.6"><model name="{name}"><static>true</static><link name="l">{vis}</link></model></sdf>')
    subprocess.run(['ros2', 'service', 'call', '/delete_entity', 'gazebo_msgs/srv/DeleteEntity', f'{{name: {name}}}'],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(['ros2', 'run', 'gazebo_ros', 'spawn_entity.py', '-entity', name, '-file', path,
                    '-x', str(x), '-y', str(y), '-z', '0'])

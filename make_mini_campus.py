#!/usr/bin/env python3
"""Mini-campus generator (context8 Option P, Stage 1 + M1 map).
Writes: world (SDF boxes only), exact map (pgm+yaml), places yaml, goals txt.
Frame: origin = centre of the home bay, bay faces +x. Interior 12 m x 10 m. World frame == map frame."""
import math, os
import numpy as np

RES = 0.05
X0, Y0, X1, Y1 = -1.5, -5.5, 11.5, 5.5          # map extent (m)
IN = (-1.0, -5.0, 11.0, 5.0)                      # free interior (x0, y0, x1, y1)
T = 0.2                                           # outer wall thickness
GREY, RED, BLUE, GREEN, YEL, ORG = (.45, .45, .45), (.75, .3, .3), (.3, .45, .8), (.35, .7, .4), (.9, .8, .3), (.9, .55, .2)

def box(name, x0, y0, x1, y1, h, col):
    return (name, (x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0, h, col)

BOXES = [
    # outer walls
    box('wall_w', -1 - T, -5 - T, -1, 5 + T, 2, GREY), box('wall_e', 11, -5 - T, 11 + T, 5 + T, 2, GREY),
    box('wall_n', -1, 5, 11, 5 + T, 2, GREY),          box('wall_s', -1, -5 - T, 11, -5, 2, GREY),
    # home bay (1.4 m clear, opens to +x)
    box('bay_n', -1, 0.7, 0.8, 0.8, 0.6, YEL), box('bay_s', -1, -0.8, 0.8, -0.7, 0.6, YEL),
    # buildings, all flush to an outer wall so no thin gaps
    box('admin',        -1, 2.5, 1.0, 5.0, 2.5, RED),
    box('auditorium',  2.5, 2.5, 6.0, 5.0, 2.5, BLUE),
    box('library',     8.0, 2.0, 11.0, 5.0, 2.5, GREEN),
    box('hostel',       -1, -5.0, 1.5, -2.5, 2.5, ORG),
    box('cafeteria',   3.0, -5.0, 6.5, -2.5, 2.5, YEL),
    box('department',  8.5, -5.0, 11.0, -2.0, 2.5, RED),
    # asymmetric features in the central plaza
    box('pillar',      6.1, -0.1, 6.9, 0.7, 2.0, GREY),
    box('L_arm_h',     8.2, 0.4, 9.4, 0.5, 1.0, GREY),
    box('L_arm_v',     8.2, -0.4, 8.3, 0.5, 1.0, GREY),
    # extra obstacles (plaza), all >= 1.0 m clear of buildings, pillar, L-wall and goal approaches
]

def yaw_q(yaw): return math.sin(yaw / 2), math.cos(yaw / 2)
PI = math.pi
PLACES = {  # name: (x, y, yaw, aliases) - each goal 0.8 m in front of the entrance, facing the building
    'home':       (0.0, 0.0, 0.0, ['base', 'parking']),
    'admin':      (1.8, 3.75, PI, ['admin block', 'administration', 'office']),
    'auditorium': (4.25, 1.7, PI / 2, ['college auditorium', 'seminar hall', 'main hall']),
    'library':    (9.5, 1.2, PI / 2, ['central library', 'books']),
    'cafeteria':  (4.75, -1.7, -PI / 2, ['canteen', 'food court']),
    'department': (9.75, -1.2, -PI / 2, ['dept', 'cs department']),
    'hostel':     (1.2, -1.7, -PI / 2, ['dormitory', 'residence']),
}

HOME = os.path.expanduser('~/limo_ws')
os.makedirs(f'{HOME}/worlds_local', exist_ok=True); os.makedirs(f'{HOME}/maps', exist_ok=True); os.makedirs(f'{HOME}/params', exist_ok=True)

# ---- world ----
m = []
for n, cx, cy, sx, sy, h, c in BOXES:
    col = f'{c[0]} {c[1]} {c[2]} 1'
    m.append(f'''    <model name="{n}"><static>true</static><pose>{cx:.3f} {cy:.3f} {h/2:.3f} 0 0 0</pose><link name="link">
      <collision name="c"><geometry><box><size>{sx:.3f} {sy:.3f} {h}</size></box></geometry></collision>
      <visual name="v"><geometry><box><size>{sx:.3f} {sy:.3f} {h}</size></box></geometry><material><ambient>{col}</ambient><diffuse>{col}</diffuse></material></visual>
    </link></model>''')
# ---- visual-only extras (no collision -> invisible to the lidar, map unchanged) ----
PAD_COL = {'home': YEL, 'admin': RED, 'auditorium': BLUE, 'library': GREEN,
           'cafeteria': YEL, 'department': RED, 'hostel': ORG}
for k, (x, y, yaw, al) in PLACES.items():
    c = PAD_COL.get(k, GREY); col = f'{c[0]} {c[1]} {c[2]} 1'
    m.append(f'''    <model name="pad_{k}"><static>true</static><pose>{x} {y} 0.005 0 0 0</pose><link name="link">
      <visual name="v"><geometry><cylinder><radius>0.3</radius><length>0.01</length></cylinder></geometry><material><ambient>{col}</ambient><diffuse>{col}</diffuse><emissive>{c[0]*.4} {c[1]*.4} {c[2]*.4} 1</emissive></material></visual>
    </link></model>''')
# destination beacon: moved by the guide via /gazebo/set_entity_state; parked underground when idle
m.append('''    <model name="beacon"><pose>0 0 -5 0 0 0</pose><link name="link"><gravity>0</gravity><kinematic>true</kinematic>
      <visual name="pole"><pose>0 0 0.75 0 0 0</pose><geometry><cylinder><radius>0.04</radius><length>1.5</length></cylinder></geometry><material><ambient>0 1 0 1</ambient><diffuse>0 1 0 1</diffuse><emissive>0 0.8 0 1</emissive></material></visual>
      <visual name="ball"><pose>0 0 1.6 0 0 0</pose><geometry><sphere><radius>0.18</radius></sphere></geometry><material><ambient>0 1 0 1</ambient><diffuse>0 1 0 1</diffuse><emissive>0 1 0 1</emissive></material></visual>
      <visual name="ring"><pose>0 0 0.02 0 0 0</pose><geometry><cylinder><radius>0.45</radius><length>0.02</length></cylinder></geometry><material><ambient>0 1 0 0.5</ambient><diffuse>0 1 0 0.5</diffuse><emissive>0 0.6 0 1</emissive></material><transparency>0.4</transparency></visual>
    </link></model>''')
world = f'''<?xml version="1.0"?>
<sdf version="1.6"><world name="mini_campus">
    <include><uri>model://sun</uri></include>
    <include><uri>model://ground_plane</uri></include>
    <plugin name="gazebo_ros_state" filename="libgazebo_ros_state.so"><ros><namespace>/gazebo</namespace></ros><update_rate>10.0</update_rate></plugin>
    <gui fullscreen="0"><camera name="user_camera"><pose>5 -9.5 11 0 0.85 1.5708</pose></camera></gui>
{chr(10).join(m)}
</world></sdf>
'''
open(f'{HOME}/worlds_local/mini_campus.world', 'w').write(world)

# ---- exact map (world == map frame) ----
W, H = int(round((X1 - X0) / RES)), int(round((Y1 - Y0) / RES))
xs = X0 + (np.arange(W) + 0.5) * RES; ys = Y0 + (np.arange(H) + 0.5) * RES
gx, gy = np.meshgrid(xs, ys)                       # row j = y index from bottom
img = np.full((H, W), 205, np.uint8)
img[(gx > IN[0]) & (gx < IN[2]) & (gy > IN[1]) & (gy < IN[3])] = 254
for n, cx, cy, sx, sy, h, c in BOXES:
    img[(abs(gx - cx) <= sx / 2) & (abs(gy - cy) <= sy / 2)] = 0
# Hollow the big blocks: only a 0.15 m wall ring stays occupied (like a real lidar map).
# A solid-filled block lets AMCL's likelihood field "park" particles inside it (every beam end scores 0 m).
for n, cx, cy, sx, sy, h, c in BOXES:
    if not n.startswith('wall') and min(sx, sy) > 0.5:
        img[(abs(gx - cx) < sx / 2 - 0.15) & (abs(gy - cy) < sy / 2 - 0.15)] = 254
with open(f'{HOME}/maps/campus_v1.pgm', 'wb') as f:
    f.write(b'P5\n%d %d\n255\n' % (W, H)); f.write(np.flipud(img).tobytes())
open(f'{HOME}/maps/campus_v1.yaml', 'w').write(
    f'image: campus_v1.pgm\nmode: trinary\nresolution: {RES}\norigin: [{X0}, {Y0}, 0.0]\n'
    'negate: 0\noccupied_thresh: 0.65\nfree_thresh: 0.196\n')

# ---- places + goals ----
with open(f'{HOME}/params/places_campus.yaml', 'w') as f:
    for k, (x, y, yaw, al) in PLACES.items():
        f.write(f'{k}: {{x: {x}, y: {y}, yaw: {yaw:.4f}, aliases: {al}}}\n')
with open(f'{HOME}/params/goals_campus.txt', 'w') as f:
    for k, (x, y, yaw, al) in PLACES.items():
        qz, qw = yaw_q(yaw); f.write(f'{x} {y} {qz:.4f} {qw:.4f}\n')

# ---- validation: reachability with 0.25 m erosion (robot half-diagonal 0.18 + margin) ----
try:
    from scipy import ndimage as ndi
    free = img == 254
    r = int(round(0.25 / RES)); yy, xx = np.ogrid[-r:r + 1, -r:r + 1]
    er = ndi.binary_erosion(free, structure=(xx * xx + yy * yy <= r * r))
    lab, _ = ndi.label(er)
    def idx(x, y): return int((y - Y0) / RES), int((x - X0) / RES)
    home_lab = lab[idx(0, 0)]
    print('home cell free after erosion:', home_lab != 0)
    for k, (x, y, yaw, al) in PLACES.items():
        print(f'  {k:11s} reachable with 0.25 m clearance:', lab[idx(x, y)] == home_lab and home_lab != 0)
except Exception:
    print('scipy unavailable: skipped reachability check')
print(f'wrote world, map {W}x{H}px, places, goals under {HOME}')

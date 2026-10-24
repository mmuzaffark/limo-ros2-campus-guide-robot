#!/usr/bin/env python3
import os, yaml, collections, numpy as np
H = os.path.expanduser('~/limo_ws')
RES, X0, Y0 = 0.05, -1.5, -5.5
raw = open(f'{H}/maps/campus_v1.pgm', 'rb').read()
w, h = map(int, raw.split(b'\n')[1].split()); off = len(raw) - w * h
img = np.frombuffer(raw[off:], np.uint8).reshape(h, w)          # row 0 = top
blocked = img != 254
R = 5                                                           # 0.25 m / 0.05
dil = np.zeros_like(blocked)
for dy in range(-R, R + 1):
    for dx in range(-R, R + 1):
        if dx * dx + dy * dy <= R * R:
            dil |= np.roll(np.roll(blocked, dy, 0), dx, 1)
free = ~dil
def cell(x, y): return h - 1 - int((y - Y0) / RES), int((x - X0) / RES)
places = yaml.safe_load(open(f'{H}/params/places_campus.yaml'))
seen = np.zeros_like(free); s = cell(0, 0); q = collections.deque([s]); seen[s] = True
while q:
    r, c = q.popleft()
    for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        rr, cc = r + dr, c + dc
        if 0 <= rr < h and 0 <= cc < w and free[rr, cc] and not seen[rr, cc]:
            seen[rr, cc] = True; q.append((rr, cc))
print('home free:', bool(free[s]))
for k, p in places.items():
    print(f'  {k:11s} reachable (0.25 m clearance):', bool(seen[cell(p["x"], p["y"])]))

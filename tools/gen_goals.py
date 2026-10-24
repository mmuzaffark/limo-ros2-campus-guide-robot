#!/usr/bin/env python3
import math, os, yaml, numpy as np
from collections import deque
from PIL import Image, ImageDraw

MAP = os.path.expanduser('~/limo_ws/maps/world_v1_edited.yaml')
OUT = os.path.expanduser('~/limo_ws/params')
HOME = (-0.511, 0.300, -1.527)
cfg = yaml.safe_load(open(MAP)); res = cfg['resolution']; ox, oy = cfg['origin'][:2]
pgm = os.path.join(os.path.dirname(MAP), cfg['image'])
img = np.array(Image.open(pgm).convert('L')).astype(float); H, W = img.shape
occ = img/255 if cfg.get('negate', 0) else (255-img)/255
free = occ < cfg['free_thresh']; wall = occ > cfg['occupied_thresh']
def to_xy(r, c): return ox+(c+.5)*res, oy+(H-1-r+.5)*res
def to_rc(x, y): return H-1-int(math.floor((y-oy)/res)), int(math.floor((x-ox)/res))

bad = np.argwhere(~free); clr = np.zeros((H, W))
for r, c in np.argwhere(free):
    d = np.sqrt(((bad-[r, c])**2).sum(1).min())
    clr[r, c] = max(d-0.5, 0)*res
hr, hc = to_rc(*HOME[:2]); seen = {(hr, hc)}; q = deque([(hr, hc)])
while q:
    r, c = q.popleft()
    for dr, dc in ((1,0),(-1,0),(0,1),(0,-1)):
        p = (r+dr, c+dc)
        if 0 <= p[0] < H and 0 <= p[1] < W and p not in seen and clr[p] >= 0.14:
            seen.add(p); q.append(p)
thr, cand = 0.20, []
while not cand and thr > 0.12:
    cand = [p for p in seen if clr[p] >= thr]; thr -= 0.01
if not cand: raise SystemExit('no reachable free cells; check map/home')
def nearest(px, py): return min(cand, key=lambda p: math.hypot(to_xy(*p)[0]-px, to_xy(*p)[1]-py))

wr, wc = np.nonzero(wall); pts = [to_xy(r, c) for r, c in zip(wr, wc)]
x0, x1 = min(p[0] for p in pts), max(p[0] for p in pts)
y0, y1 = min(p[1] for p in pts), max(p[1] for p in pts)
cx, cy = (x0+x1)/2, (y0+y1)/2
snap = lambda a: round(a/(math.pi/2))*(math.pi/2)
goals = []
for name, (px, py) in [('C1',(x1,y1)),('C2',(x1,y0)),('C3',(x0,y0)),('C4',(x0,y1))]:
    x, y = to_xy(*nearest(px, py)); goals.append((name, x, y, snap(math.atan2(cy-y, cx-x))))
x, y = to_xy(*nearest(cx, cy)); goals.append(('center', x, y, 0.0))
goals.append(('home',)+HOME)

with open(f'{OUT}/goals.txt', 'w') as f:
    for n, x, y, a in goals: f.write(f'{x:.4f} {y:.4f} {math.sin(a/2):.4f} {math.cos(a/2):.4f}\n')
with open(f'{OUT}/places_draft.yaml', 'w') as f:
    for n, x, y, a in goals: f.write(f'{n}: {{x: {x:.3f}, y: {y:.3f}, yaw: {a:.3f}}}\n')
S = 12; im = Image.open(pgm).convert('RGB').resize((W*S, H*S), Image.NEAREST); dr = ImageDraw.Draw(im)
print(f'wall bbox x[{x0:.2f},{x1:.2f}] y[{y0:.2f},{y1:.2f}]  reachable cells {len(seen)}  clearance used >= {thr+0.01:.2f} m')
for i, (n, x, y, a) in enumerate(goals, 1):
    r, c = to_rc(x, y); px, py = (c+.5)*S, (r+.5)*S
    dr.ellipse([px-8, py-8, px+8, py+8], fill=(255, 0, 0))
    dr.line([px, py, px+24*math.cos(a), py-24*math.sin(a)], fill=(0, 0, 255), width=3)
    dr.text((px+10, py-22), 'H' if n == 'home' else str(i), fill=(255, 0, 0))
    print(f'{i} {n:7s} x={x:+.3f} y={y:+.3f} yaw={math.degrees(a):+4.0f} deg  clearance={clr[r, c]:.2f} m')
im.save(f'{OUT}/goals_preview.png')

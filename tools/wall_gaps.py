#!/usr/bin/env python3
import os, sys, numpy as np, yaml
M = os.path.expanduser('~/limo_ws/maps/' + (sys.argv[1] if len(sys.argv) > 1 else 'campus_slam'))
y = yaml.safe_load(open(M + '.yaml')); res = y['resolution']; ox, oy = y['origin'][0], y['origin'][1]
raw = open(M + '.pgm', 'rb').read(); tok = []; i = 0
while len(tok) < 4:
    while raw[i:i+1].isspace(): i += 1
    if raw[i:i+1] == b'#':
        while raw[i:i+1] != b'\n': i += 1
        continue
    j = i
    while not raw[j:j+1].isspace(): j += 1
    tok.append(raw[i:j]); i = j
w, h = int(tok[1]), int(tok[2]); img = np.frombuffer(raw[i+1:], np.uint8)[:w*h].reshape(h, w)
rc = lambda x, yy: (h - 1 - int((yy - oy) / res), int((x - ox) / res))
print('origin', y['origin'], 'size', w, h)
print('ASCII, x -1.2..1.4 across, y 1.3..-1.3 down  (# wall, . free, ? unknown)')
for yy in np.arange(1.3, -1.31, -0.05):
    print(''.join('#' if img[rc(xx, yy)] == 0 else ('.' if img[rc(xx, yy)] >= 250 else '?') for xx in np.arange(-1.2, 1.41, 0.05)))
for name, wy in (('bay south wall y=-0.75', -0.75), ('bay north wall y=+0.75', 0.75)):
    gap = [round(float(xx), 2) for xx in np.arange(-0.95, 0.80, 0.05)
           if not (img[rc(xx, wy)[0]-3:rc(xx, wy)[0]+4, rc(xx, wy)[1]] == 0).any()]
    print(name, '-> gaps at x =', gap if gap else 'none')

#!/usr/bin/env python3
import sys, os, math, yaml, numpy as np
from PIL import Image
y = os.path.expanduser(sys.argv[1]); cfg = yaml.safe_load(open(y))
img = np.array(Image.open(os.path.join(os.path.dirname(y), cfg['image'])).convert('L'))
H, W = img.shape; r, c = np.nonzero(img < 50)
p = np.stack([c, H-1-r], 1) * cfg['resolution']
best = None
for th in np.arange(-45, 45.01, 0.25):
    t = math.radians(th); R = np.array([[math.cos(t), -math.sin(t)], [math.sin(t), math.cos(t)]])
    q = p @ R.T; a = np.ptp(q[:, 0]) * np.ptp(q[:, 1])
    if best is None or a < best[1]: best = (th, a)
print(f'tilt of walls: {best[0]:+.2f} deg   predicted position error at 1.7 m radius: {1.7*math.sin(math.radians(abs(best[0]))):.2f} m')

#!/usr/bin/env python3
import os, re
from PIL import Image, ImageDraw, ImageFont, ImageOps
H = os.path.expanduser('~/limo_ws')
D = f'{H}/labels'; TX = f'{D}/materials/textures'; SC = f'{D}/materials/scripts'
WORLD = f'{H}/worlds_local/mini_campus.world'
os.makedirs(TX, exist_ok=True); os.makedirs(SC, exist_ok=True)
YAW = -1.5708   # -90 deg = clockwise seen from above
FLIP = 'none'   # none | h | v | hv  -> change and rerun if text looks mirrored
# name: (text, x, y, z, width, height)   z = roof height 2.5 + 0.02
L = {
 'admin':      ('ADMIN BLOCK',  0.0,   3.75, 2.52, 1.8, 0.45),
 'auditorium': ('AUDITORIUM',   4.25,  3.75, 2.52, 2.3, 0.6),
 'library':    ('LIBRARY',      9.5,   3.5,  2.52, 2.4, 0.6),
 'hostel':     ('HOSTEL',       0.25, -3.75, 2.52, 2.0, 0.5),
 'cafeteria':  ('CAFETERIA',    4.75, -3.75, 2.52, 2.3, 0.6),
 'department': ('DEPARTMENT',   9.75, -3.5,  2.52, 2.4, 0.6),
 'home':       ('HOME',        -0.55,  0.0,  0.02, 0.7, 0.2),
}
fp = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
mat, sdf = '', ''
for k, (t, x, y, z, w, h) in L.items():
    img = Image.new('RGB', (512, 128), (20, 30, 60)); d = ImageDraw.Draw(img)
    size = 80
    while True:
        f = ImageFont.truetype(fp, size) if os.path.exists(fp) else ImageFont.load_default()
        b = d.textbbox((0, 0), t, font=f)
        if b[2] - b[0] < 480 or size < 16: break
        size -= 4
    d.text(((512 - b[2] - b[0]) / 2, (128 - b[3] - b[1]) / 2), t, font=f, fill=(255, 255, 255))
    if 'h' in FLIP: img = ImageOps.mirror(img)
    if 'v' in FLIP: img = ImageOps.flip(img)
    img.save(f'{TX}/{k}.png')
    mat += f'material Label/{k}\n{{\n technique\n {{\n  pass\n  {{\n   lighting off\n   texture_unit\n   {{\n    texture {k}.png\n   }}\n  }}\n }}\n}}\n'
    sdf += f'''  <model name="label_{k}"><static>true</static><pose>{x} {y} {z} 0 0 {YAW}</pose><link name="link">
    <visual name="v"><cast_shadows>false</cast_shadows><geometry><plane><normal>0 0 1</normal><size>{w} {h}</size></plane></geometry>
    <material><script><uri>file://{SC}</uri><uri>file://{TX}</uri><name>Label/{k}</name></script></material></visual>
  </link></model>
'''
open(f'{SC}/labels.material', 'w').write(mat)
w = open(WORLD).read()
w = re.sub(r'<!-- LABELS_BEGIN -->.*?<!-- LABELS_END -->\n?', '', w, flags=re.S)
w = w.replace('</world>', f'<!-- LABELS_BEGIN -->\n{sdf}<!-- LABELS_END -->\n</world>')
open(WORLD, 'w').write(w)
print('labels written:', ', '.join(L))

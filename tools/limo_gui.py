#!/usr/bin/env python3
"""Limo Campus Guide GUI: building buttons, text box, voice (mic / audio file), status, cancel."""
import os, re, shlex, shutil, signal, subprocess, threading, queue, time, yaml
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext

HOME = os.path.expanduser('~')
PLACES = f'{HOME}/limo_ws/params/places_campus.yaml'
GUIDE = f'{HOME}/limo_ws/guide'
CLIPS = f'{HOME}/clips'
REC_SEC = 5
NOISE = ('RTPS_READER_HISTORY', 'loading speech model')
COL = {'admin': '#e57373', 'auditorium': '#64b5f6', 'library': '#81c784',
       'hostel': '#ffb74d', 'cafeteria': '#fff176', 'department': '#e57373'}

def sh(cmd):
    return subprocess.Popen(['bash', '-c', f'source ~/env.sh && exec {cmd}'],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
                            cwd=HOME, env={**os.environ, 'PYTHONUNBUFFERED': '1'}, start_new_session=True)

class App:
    def __init__(s, root):
        s.root = root; root.title('Limo Campus Guide'); root.geometry('600x700')
        s.proc = None; s.q = queue.Queue(); s.dest = ''; s.leg = 1.0; s.ctrl = []
        try: s.places = yaml.safe_load(open(PLACES)) or {}
        except Exception: s.places = {}
        names = [k for k in s.places if k != 'home']
        tk.Label(root, text='Where do you want to go?', font=('DejaVu Sans', 14, 'bold')).pack(pady=(10, 4))
        f = tk.Frame(root); f.pack()
        for i, n in enumerate(names):
            b = tk.Button(f, text=n.capitalize(), width=14, height=2, bg=COL.get(n, '#dddddd'),
                          font=('DejaVu Sans', 11, 'bold'), command=lambda n=n: s.trip(n))
            b.grid(row=i // 3, column=i % 3, padx=5, pady=5); s.ctrl.append(b)
        t = tk.Frame(root); t.pack(pady=8, fill='x', padx=14)
        s.entry = tk.Entry(t, font=('DejaVu Sans', 11)); s.entry.pack(side='left', fill='x', expand=True)
        s.entry.bind('<Return>', lambda e: s.send())
        sb = tk.Button(t, text='Send', command=s.send); sb.pack(side='left', padx=4)
        s.ctrl += [s.entry, sb]
        v = tk.Frame(root); v.pack(pady=4)
        mb = tk.Button(v, text=f'Mic ({REC_SEC} s)', width=16, height=2, command=s.mic)
        fb = tk.Button(v, text='Audio file...', width=16, height=2, command=s.pick)
        mb.grid(row=0, column=0, padx=5); fb.grid(row=0, column=1, padx=5); s.ctrl += [mb, fb]
        s.ret = tk.BooleanVar(value=True)
        tk.Checkbutton(root, text='Return home after arriving', variable=s.ret,
                       font=('DejaVu Sans', 11)).pack()
        tk.Button(root, text='CANCEL and go home', bg='#c62828', fg='white', font=('DejaVu Sans', 11, 'bold'),
                  height=2, command=s.cancel).pack(pady=8, fill='x', padx=14)
        s.status = tk.StringVar(value='Idle')
        tk.Label(root, textvariable=s.status, font=('DejaVu Sans', 12)).pack()
        s.bar = ttk.Progressbar(root, length=500, maximum=100); s.bar.pack(pady=4)
        s.log = scrolledtext.ScrolledText(root, height=14, font=('DejaVu Sans Mono', 9)); s.log.pack(fill='both', expand=True, padx=8, pady=6)
        root.protocol('WM_DELETE_WINDOW', s.close); s.poll()

    def say(s, m): s.log.insert('end', m + '\n'); s.log.see('end')
    def busy(s, b):
        for w in s.ctrl: w.config(state='disabled' if b else 'normal')
    def running(s): return s.proc is not None and s.proc.poll() is None

    def run(s, cmd, label):
        if s.running(): return
        s.busy(True); s.status.set(label); s.bar['value'] = 0
        p = s.proc = sh(cmd)
        def rd():
            for l in p.stdout: s.q.put((p, l.rstrip()))
            p.wait(); s.q.put((p, None))
        threading.Thread(target=rd, daemon=True).start()

    def nr(s): return '' if s.ret.get() else ' --no-return'
    def trip(s, name): s.run(f'python3 -u {GUIDE}/guide_manager.py --once {shlex.quote("take me to the " + name)}{s.nr()}', f'Starting: {name}')
    def send(s):
        t = s.entry.get().strip()
        if t: s.entry.delete(0, 'end'); s.say(f'> {t}'); s.run(f'python3 -u {GUIDE}/guide_manager.py --once {shlex.quote(t)}{s.nr()}', 'Sending command')
    def voice(s, wav): s.run(f'python3 -u {GUIDE}/voice_guide.py --wav {shlex.quote(wav)}{s.nr()}', 'Transcribing...')

    def pick(s):
        os.makedirs(CLIPS, exist_ok=True)
        f = filedialog.askopenfilename(initialdir=CLIPS, filetypes=[('Audio', '*.wav *.m4a *.mp3 *.ogg'), ('All', '*')])
        if not f: return
        if not f.lower().endswith('.wav'):
            out = f'{CLIPS}/_gui.wav'
            subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', f, '-ar', '16000', '-ac', '1', out])
            f = out
        s.play_then(f)

    def play_then(s, f):
        s.busy(True); s.status.set('Playing clip...'); s.say(f'audio: {f}')
        def job():
            ok = False
            try:
                if shutil.which('powershell.exe'):
                    win = '/mnt/c/Users/Public/limo_clip.wav'
                    shutil.copy(f, win)
                    r = subprocess.run(['powershell.exe', '-NoProfile', '-Command',
                        "(New-Object Media.SoundPlayer 'C:\\Users\\Public\\limo_clip.wav').PlaySync()"],
                        capture_output=True, timeout=60)
                    ok = r.returncode == 0
                if not ok and shutil.which('ffplay'):
                    ok = subprocess.run(['ffplay', '-nodisp', '-autoexit', '-loglevel', 'error', f],
                                        timeout=60).returncode == 0
            except Exception as e:
                s.q.put(('call', lambda: s.say(f'playback error: {e}')))
            if not ok: s.q.put(('call', lambda: s.say('could not play the clip, continuing')))
            s.q.put(('call', lambda: s.voice(f)))
        threading.Thread(target=job, daemon=True).start()

    def mic(s):
        if not shutil.which('parecord'):
            s.say('parecord missing: sudo apt install -y pulseaudio-utils (mic also needs a Dell mic; use Audio file over AnyDesk)'); return
        os.makedirs(CLIPS, exist_ok=True); s.busy(True); s.status.set(f'Recording {REC_SEC} s - speak now')
        wav = f'{CLIPS}/mic_{int(time.time())}.wav'
        def rec():
            subprocess.run(['timeout', '-s', 'INT', str(REC_SEC), 'parecord', '--channels=1', '--rate=16000', '--file-format=wav', wav])
            s.q.put(('call', lambda: s.after_rec(wav)))
        threading.Thread(target=rec, daemon=True).start()
    def after_rec(s, wav):
        s.busy(False)
        if not os.path.exists(wav) or os.path.getsize(wav) < 5000: s.status.set('No audio captured'); s.say('no mic audio; use Audio file'); return
        s.voice(wav)

    def kill(s):
        if s.running():
            try: os.killpg(s.proc.pid, signal.SIGTERM)
            except Exception: pass
            try: s.proc.wait(timeout=3)
            except Exception: pass
    def cancel(s):
        s.kill(); h = s.places.get('home', {'x': 0.0, 'y': 0.0, 'yaw': 0.0}); import math
        g = ('{pose: {header: {frame_id: map}, pose: {position: {x: %s, y: %s}, orientation: {z: %.4f, w: %.4f}}}}' % (h['x'], h['y'], math.sin(h['yaw'] / 2), math.cos(h['yaw'] / 2)))
        s.say('cancel -> going home'); s.proc = None
        s.run(f'ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose {shlex.quote(g)}', 'Cancelled - returning home')

    def handle(s, l):
        if not l or any(n in l for n in NOISE): return
        s.say(l)
        m = re.search(r'heading to ([\w ]+?) \(attempt', l)
        if m: s.dest = m.group(1); s.leg = 0; s.status.set('Returning home' if s.dest == 'home' else f'Heading to {s.dest}')
        m = re.search(r'([\d.]+) m to go', l)
        if m:
            d = float(m.group(1)); s.leg = max(s.leg, d, 0.1)
            s.bar['value'] = 100 * (1 - d / s.leg); s.status.set(f'{"Returning home" if s.dest == "home" else "Heading to " + s.dest}: {d:.1f} m to go')
        if 'We have arrived' in l: s.status.set(f'Arrived at {s.dest}'); s.bar['value'] = 100
        if 'staying at the' in l: s.status.set(f'Arrived at {s.dest} - staying here')
        if 'waiting' in l and 'then returning' in l: s.status.set(f'Waiting at {s.dest}')
        if 'back at my base' in l: s.status.set('Back at base'); s.bar['value'] = 100

    def poll(s):
        try:
            while True:
                it = s.q.get_nowait()
                if it[0] == 'call': it[1]()
                elif it[0] is not s.proc: continue
                elif it[1] is None:
                    s.busy(False)
                    if not s.status.get().startswith(('Back', 'Cancelled', 'Arrived')): s.status.set('Idle')
                else: s.handle(it[1])
        except queue.Empty: pass
        s.root.after(100, s.poll)
    def close(s): s.kill(); s.root.destroy()

if __name__ == '__main__':
    r = tk.Tk(); App(r); r.mainloop()

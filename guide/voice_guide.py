#!/usr/bin/env python3
"""Voice front-end for the Limo campus guide (Phase 5).

Push-to-talk: press Enter, speak, press Enter again. The speech is transcribed
offline with faster-whisper and passed to the same parser as the text guide.
Replies are spoken through the Windows voice.

Usage:
  python3 voice_guide.py                     # push-to-talk loop (type text instead of Enter to skip the mic)
  python3 voice_guide.py --seconds 4         # fixed 4 s recording after each Enter
  python3 voice_guide.py --wav clip.wav      # transcribe a file and run it (testing)
  python3 voice_guide.py --mic-test          # record 3 s and print the level + transcript, no robot
Microphone: WSLg PulseAudio (needs `sudo apt install pulseaudio-utils`).
"""
import argparse, os, subprocess, sys, tempfile, time, wave
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guide_manager as gm


def record(path, seconds=0.0, max_s=10.0):
    """Record 16 kHz mono WAV from the default PulseAudio source."""
    cmd = ['parecord', '--channels=1', '--rate=16000', '--format=s16le', '--file-format=wav', path]
    try:
        p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    except FileNotFoundError:
        raise SystemExit('parecord not found: run  sudo apt install -y pulseaudio-utils')
    if seconds > 0:
        time.sleep(seconds)
    else:
        print('  ... listening, press Enter when done', flush=True)
        t0 = time.time()
        try:
            input()
        except EOFError:
            pass
        if time.time() - t0 > max_s:
            print(f'  (only the first part is kept, max {max_s:.0f} s)')
    p.terminate(); p.wait(timeout=3)
    return path


def level(path):
    with wave.open(path) as w:
        data = w.readframes(w.getnframes())
        x = np.frombuffer(data, dtype=np.int16).astype(np.float64)
        return w.getnframes() / w.getframerate(), (int(np.sqrt(np.mean(x * x))) if x.size else 0)


class Ear:
    def __init__(self, places, model='base.en', device='cpu'):
        from faster_whisper import WhisperModel
        compute = 'float16' if device == 'cuda' else 'int8'
        print(f'loading speech model {model} on {device} ...', flush=True)
        self.m = WhisperModel(model, device=device, compute_type=compute)
        names = sorted({n for n in places} | {a for p in places.values() for a in p['aliases']})
        self.prompt = 'Commands for a campus guide robot. Places: ' + ', '.join(names) + '.'

    def hear(self, path):
        segs, _ = self.m.transcribe(path, language='en', beam_size=3, vad_filter=True,
                                    initial_prompt=self.prompt)
        return ' '.join(s.text for s in segs).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', default='base.en', help='whisper model: tiny.en, base.en, small.en')
    ap.add_argument('--device', default='cpu', choices=['cpu', 'cuda'])
    ap.add_argument('--seconds', type=float, default=0.0, help='fixed recording length (0 = Enter to stop)')
    ap.add_argument('--wav', help='transcribe this file instead of the microphone, run it, exit')
    ap.add_argument('--mic-test', action='store_true')
    ap.add_argument('--wait', type=float, default=10.0, help='seconds to wait at the destination')
    ap.add_argument('--no-speak', action='store_true', help='do not speak replies')
    ap.add_argument('--no-return', action='store_true', help='stay at the destination instead of returning home')
    ap.add_argument('--places', default=gm.PLACES_FILE)
    a = ap.parse_args()
    places = gm.load_places(a.places)
    ear = Ear(places, a.model, a.device)

    if a.mic_test:
        f = record(tempfile.mktemp(suffix='.wav'), seconds=3)
        dur, rms = level(f)
        print(f'recorded {dur:.1f} s, level {rms} (silence is < 100; speech is usually > 500)')
        print('heard:', repr(ear.hear(f)))
        return

    g = gm.Guide(places, wait_s=a.wait, speak=not a.no_speak, return_home=not a.no_return)
    try:
        if a.wav:
            text = ear.hear(a.wav)
            g.log(f'heard: "{text}"  ->  {gm.parse(text, places)}')
            g.handle(text) if text else g.say("I did not catch that.")
            return
        g.say('Hello, I am your campus guide. Where would you like to go?')
        print("\nPress Enter, speak, press Enter. Or type a command. 'quit' to exit.\n")
        while True:
            try:
                typed = input('[Enter to talk] > ').strip()
            except EOFError:
                break
            if typed:
                text = typed
            else:
                f = record(tempfile.mktemp(suffix='.wav'), seconds=a.seconds)
                dur, rms = level(f)
                if rms < 100:
                    g.say("I did not hear anything. Please check the microphone.")
                    g.log(f'(recorded {dur:.1f} s, level {rms})'); continue
                t0 = time.time(); text = ear.hear(f)
                g.log(f'heard: "{text}"  ({time.time() - t0:.1f} s)')
                if not text:
                    g.say("I did not catch that. Please say it again."); continue
            if not g.handle(text):
                g.say('Goodbye.'); break
    finally:
        g.close()


if __name__ == '__main__':
    main()

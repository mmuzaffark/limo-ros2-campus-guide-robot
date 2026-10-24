#!/usr/bin/env python3
"""Limo campus guide manager (Phase 4).

Text command -> place -> Nav2 goal -> wait at the place -> return home.

Usage:
  python3 guide_manager.py                       # interactive prompt
  python3 guide_manager.py --once "take me to the library" [--wait 10]
  python3 guide_manager.py --parse "take me to the canteen"   # parser only, no ROS

Commands understood (free text):
  take me to / go to / guide me to <place>  -> trip: go, wait, return home
  go home / come back / return              -> go home now
  list / places / help                      -> list known places
  where are you                             -> current pose
  quit / exit
"""
import argparse, math, os, re, subprocess, sys, time

PLACES_FILE = os.path.expanduser('~/limo_ws/params/places_campus.yaml')
HOME_WORDS = ('go home', 'come back', 'return home', 'return', 'go back', 'back home', 'home')
LIST_WORDS = ('list', 'places', 'help', 'what places', 'where can you go')
WHERE_WORDS = ('where are you', 'where am i', 'position', 'status')
QUIT_WORDS = ('quit', 'exit', 'bye')
FILLER = r"\b(please|can you|could you|would you|kindly|the|a|an|to|me|take|go|guide|bring|show|way|i want|want|need|let's|lets|now)\b"


def load_places(path=PLACES_FILE):
    import yaml
    data = yaml.safe_load(open(path))
    places = {}
    for name, v in data.items():
        places[name] = {'x': float(v['x']), 'y': float(v['y']), 'yaw': float(v['yaw']),
                        'aliases': [a.lower() for a in v.get('aliases', [])]}
    if 'home' not in places:
        raise SystemExit(f'{path}: needs a "home" entry')
    return places


def _score(a, b):
    try:
        from rapidfuzz import fuzz
        return max(fuzz.ratio(a, b), fuzz.partial_ratio(a, b) if min(len(a), len(b)) >= 4 else 0)
    except ImportError:
        import difflib
        r = difflib.SequenceMatcher(None, a, b).ratio() * 100
        if min(len(a), len(b)) >= 4 and (a in b or b in a):
            r = max(r, 90)
        return r


def match_place(text, places, threshold=70):
    """Return (place_name, score) or (None, best_score)."""
    t = re.sub(FILLER, ' ', text.lower())
    t = re.sub(r'[^a-z0-9 ]', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    if not t:
        return None, 0
    best, best_s = None, 0
    for name, p in places.items():
        for cand in [name.lower()] + p['aliases']:
            s = _score(t, cand)
            # also score each word window of the command against the candidate
            words = t.split(); n = len(cand.split())
            for i in range(len(words)):
                s = max(s, _score(' '.join(words[i:i + n]), cand))
            if s > best_s:
                best, best_s = name, s
    return (best, best_s) if best_s >= threshold else (None, best_s)


def parse(text, places):
    """Return (intent, place). intent in trip, home, list, where, quit, unknown."""
    t = text.lower().strip()
    if not t:
        return 'unknown', None
    if any(t == w or t.startswith(w + ' ') for w in QUIT_WORDS):
        return 'quit', None
    if any(w in t for w in WHERE_WORDS):
        return 'where', None
    if any(t == w or t.startswith(w) for w in LIST_WORDS):
        return 'list', None
    place, _ = match_place(t, {k: v for k, v in places.items() if k != 'home'})
    if place:
        return 'trip', place
    if any(w in t for w in HOME_WORDS) or match_place(t, {'home': places['home']})[0]:
        return 'home', 'home'
    return 'unknown', None


class Guide:
    def __init__(self, places, wait_s=10.0, retries=1, goal_timeout=180.0, speak=False, return_home=True):
        import rclpy
        from nav2_simple_commander.robot_navigator import BasicNavigator
        from tf2_ros import Buffer, TransformListener
        from gazebo_msgs.srv import SetEntityState
        self.places, self.wait_s, self.retries, self.goal_timeout = places, wait_s, retries, goal_timeout
        self.speak = speak
        self.return_home = return_home
        rclpy.init()
        self.nav = BasicNavigator(node_name='guide_manager')
        # helper node, spun by the TF listener thread: TF lookups + Gazebo beacon service
        self.aux = rclpy.create_node('guide_aux')
        self.tfb = Buffer(); self.tfl = TransformListener(self.tfb, self.aux, spin_thread=True)
        self.beacon_cli = self.aux.create_client(SetEntityState, '/gazebo/set_entity_state')

    def log(self, msg):
        print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

    def say(self, msg):
        """Log, and speak through the Windows voice when --speak is on (non-blocking)."""
        self.log(msg)
        if self.speak:
            t = msg.replace("'", "''")
            try:
                subprocess.Popen(['powershell.exe', '-NoProfile', '-Command',
                                  f"Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{t}')"],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except OSError:
                pass

    def beacon(self, name=None):
        """Move the green Gazebo beacon to a place (None = hide it underground)."""
        from gazebo_msgs.srv import SetEntityState
        if not self.beacon_cli.wait_for_service(timeout_sec=0.5):
            return
        req = SetEntityState.Request(); req.state.name = 'beacon'; req.state.reference_frame = 'world'
        if name:
            req.state.pose.position.x, req.state.pose.position.y = self.places[name]['x'], self.places[name]['y']
        else:
            req.state.pose.position.z = -5.0
        req.state.pose.orientation.w = 1.0
        fut = self.beacon_cli.call_async(req); t0 = time.time()
        while not fut.done() and time.time() - t0 < 2:
            time.sleep(0.05)

    def _pose(self, name):
        from geometry_msgs.msg import PoseStamped
        p = self.places[name]
        ps = PoseStamped()
        ps.header.frame_id = 'map'          # stamp 0 = use latest transform (sim-time safe)
        ps.pose.position.x, ps.pose.position.y = p['x'], p['y']
        ps.pose.orientation.z, ps.pose.orientation.w = math.sin(p['yaw'] / 2), math.cos(p['yaw'] / 2)
        return ps

    def goto(self, name):
        """Navigate to a place; returns True on success."""
        from nav2_simple_commander.robot_navigator import TaskResult
        for attempt in range(1 + self.retries):
            self.beacon(name)
            self.log(f"heading to {name} (attempt {attempt + 1})")
            if not self.nav.goToPose(self._pose(name)):
                self.log('goal rejected'); continue
            t0 = time.time(); last = 0
            while not self.nav.isTaskComplete():
                fb = self.nav.getFeedback()
                if fb and time.time() - last > 5:
                    self.log(f"  {fb.distance_remaining:.1f} m to go"); last = time.time()
                if time.time() - t0 > self.goal_timeout:
                    self.log('  timeout, cancelling'); self.nav.cancelTask(); break
            r = self.nav.getResult()
            if r == TaskResult.SUCCEEDED:
                self.say(f"We have arrived at the {name}." if name != 'home' else "I am back at my base."); return True
            self.log(f"  result: {r}")
        return False

    def trip(self, name):
        self.say(f"Sure, please follow me to the {name}.")
        reached = self.goto(name)
        if reached and not self.return_home:
            self.log(f"staying at the {name} (return to home is off)")
            self.log('ready for the next request')
            return True
        if not reached:
            self.say(f"Sorry, I could not reach the {name}. I am going back.")
        else:
            self.log(f"waiting {self.wait_s:.0f} s at the {name}, then returning home")
            time.sleep(self.wait_s)
        ok = self.goto('home')
        self.beacon(None)
        self.log('ready for the next request' if ok else 'FAILED to return home')
        return ok

    def where(self):
        from rclpy.time import Time
        t0 = time.time()
        while time.time() - t0 < 3:
            try:
                tr = self.tfb.lookup_transform('map', 'base_link', Time())
                x, y = tr.transform.translation.x, tr.transform.translation.y
                near = min(self.places, key=lambda k: math.hypot(self.places[k]['x'] - x, self.places[k]['y'] - y))
                d = math.hypot(self.places[near]['x'] - x, self.places[near]['y'] - y)
                self.say(f"I am near the {near}." if d < 1.0 else f"I am between places, closest is the {near}.")
                self.log(f"pose ({x:.2f}, {y:.2f}), {d:.2f} m from {near}")
                return
            except Exception:
                time.sleep(0.2)
        self.log('pose not available')

    def handle(self, text):
        t = text.strip().lower()
        if t in ('return off', 'no return', 'stay'):
            self.return_home = False; self.say('Okay, I will stay at the destination.'); return True
        if t in ('return on', 'auto return'):
            self.return_home = True; self.say('Okay, I will return to base after each trip.'); return True
        intent, place = parse(text, self.places)
        if intent == 'trip':
            self.trip(place)
        elif intent == 'home':
            self.say('Going back to my base.'); self.goto('home'); self.beacon(None)
        elif intent == 'list':
            self.say('I can take you to the ' + ', the '.join(k for k in self.places if k != 'home') + '.')
        elif intent == 'where':
            self.where()
        elif intent == 'quit':
            return False
        else:
            self.say("Sorry, I don't know that place. Say list to hear the places.")
            self.log(f"(heard: '{text}')")
        return True

    def close(self):
        import rclpy
        try:
            self.aux.destroy_node()
        except Exception:
            pass
        self.nav.destroy_node(); rclpy.shutdown()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--once', help='run one command and exit')
    ap.add_argument('--parse', help='parser test only (no ROS)')
    ap.add_argument('--wait', type=float, default=10.0, help='seconds to wait at the destination')
    ap.add_argument('--places', default=PLACES_FILE)
    ap.add_argument('--speak', action='store_true', help='speak replies through the Windows voice')
    ap.add_argument('--no-return', action='store_true', help='stay at the destination instead of returning home')
    a = ap.parse_args()
    places = load_places(a.places)
    if a.parse is not None:
        print(parse(a.parse, places)); return
    g = Guide(places, wait_s=a.wait, speak=a.speak, return_home=not a.no_return)
    try:
        if a.once:
            g.handle(a.once); return
        g.log("guide ready. Try: 'take me to the auditorium', 'list', 'go home', 'quit'")
        while True:
            try:
                text = input('you> ')
            except EOFError:
                break
            if not g.handle(text):
                break
    finally:
        g.close()


if __name__ == '__main__':
    main()

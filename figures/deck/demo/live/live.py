#!/usr/bin/env python3
"""DoorFlow live: change the simulator code, save, and watch the new simulation in your browser right away.

    Windows:              double-click start_live.bat   (or, in this folder:  py -3 live.py)
    Linux / WSL / macOS:  python3 figures/deck/demo/live/live.py

Needs Python 3.8+ (standard library only) and g++ with C++17:
    Windows      winget install BrechtSanders.WinLibs.POSIX.UCRT     (or MSYS2:  pacman -S mingw-w64-ucrt-x86_64-gcc)
    Linux / WSL  sudo apt install g++

What it does
  1. First start: copies the project's simulator source (experiment-materials/网络协议方向/src/dev_src_p78) to a work folder
     (default <home>/doorflow_live), adds the per-tick position dump of ../demo_dump.patch, builds it with g++ (a few
     minutes, only once) and opens http://127.0.0.1:8765 in the browser.
  2. Runs two simulations at the same time and streams them into the page while they are being computed:
     left = no door control, right = DoorFlow, both built from YOUR code (official room map, 250 robots, seed 9700,
     planner seed 101 by default). Stuck robots and jammed doors turn red automatically.
  3. Watches the work folder. Save any .cpp / .h file under <work>/sim: only the changed files are recompiled and both
     runs start again. Save <work>/settings.json: the runs restart without compiling (fleet size, seeds, ticks, switches).
     Compiler errors are shown in the page; the last good run stays on screen.

Options:  --work FOLDER   --port 8765   --jobs N   --no-browser
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
SRC = REPO / 'experiment-materials' / '网络协议方向' / 'src' / 'dev_src_p78'
HARNESS = REPO / 'experiment-materials' / '网络协议方向' / 'harness'
PATCH = HERE.parent / 'demo_dump.patch'
RG_FILE = REPO / 'experiment-materials' / 'archive' / 'tools' / 'replay_report' / 'region_graph_room64.json'
REF_FILE = HERE.parent / 'demo_stats.json'
IS_WIN = os.name == 'nt'
EXE = 'lifelong.exe' if IS_WIN else 'lifelong'
# switching these off = "no door control" (champion assignment + fixed executor), as in figures/part3/rerun/ablation.py
NONE_OFF = ['ROBOT_BRIDGE_CREDIT', 'ROBOT_CUT2_CREDIT', 'ROBOT_BMAC', 'ROBOT_LMAC', 'ROBOT_ACTIVE_CAP',
            'ROBOT_PFC_WD', 'ROBOT_PFC_WD_DRAIN', 'ROBOT_NET']
# same flags as build_linux.sh, plus -pipe (no temp files)
FLAGS = ['-std=c++17', '-O3', '-DNDEBUG', '-pipe', '-Wuninitialized', '-Wmaybe-uninitialized', '-Werror=uninitialized',
         '-Werror=maybe-uninitialized', '-Ilinux_shim', '-include', 'linux_shim/port_prelude.h', '-Iinc', '-Idefault_planner']
SIM_ARGS = ['-a', '10', '-n', '1000', '-t', '150', '-x', '100', '-p', '30000', '-c', '3', '-d', '3']   # as run_demo.py
CODE_DIRS = ('src', 'inc', 'default_planner', 'linux_shim')
CODE_EXT = ('.cpp', '.h', '.hpp')
STUCK_TICKS, RADIUS, JAM_MIN = 12, 5, 8   # same rules as build_demo.py
REF = dict(instance='room250', seed=9700, planner_seed=101, ticks=5000)   # conditions of ../demo_stats.json
DEFAULT_SETTINGS = {
    "instance": "room250",
    "seed": 9700,
    "planner_seed": 101,
    "ticks": 5000,
    "overrides": {},
    "_help": [
        "Save this file and both runs restart (no compiling).",
        "instance: room200, room250 or room300 = the official room map with 200 / 250 / 300 robots.",
        "seed: breakdown (delay) seed; planner_seed: the planner's random seed; ticks: run length (shorter = faster).",
        "overrides: change DoorFlow's switches and numbers for the right-hand run, e.g. {\"ROBOT_BMAC_APRON\": \"3\"}",
        "  (door area 3 cells instead of 4). A value of null switches that variable off, e.g. {\"ROBOT_PFC_WD\": null}.",
        "The page lists every variable the run uses under 'settings in use'."
    ]
}


def log(msg):
    print(time.strftime('%H:%M:%S'), msg, flush=True)


def default_work():
    home = Path.home()
    if IS_WIN and not str(home).isascii():   # MinGW g++ can fail on non-ASCII folder names: use C:\doorflow_live
        return Path(home.anchor) / 'doorflow_live'
    return home / 'doorflow_live'


def apply_patch(target, patch):
    """Apply a unified diff with Python (no 'patch' program needed). Same result as GNU patch: context lines keep their own
    ending (the file mixes CRLF / LF), added lines are written exactly as in the patch."""
    lines = target.read_bytes().split(b'\n')
    plines = patch.read_bytes().split(b'\n')
    if plines and plines[-1] == b'':
        plines.pop()
    hunks, cur = [], None
    for raw in plines:
        raw = raw.rstrip(b'\r')
        if raw.startswith(b'@@'):
            cur = []
            hunks.append(cur)
        elif cur is None or raw.startswith((b'---', b'+++')):
            continue
        else:
            cur.append((raw[:1] or b' ', raw[1:]))
    for hunk in hunks:
        old = [t for op, t in hunk if op in (b' ', b'-')]
        new = [t for op, t in hunk if op in (b' ', b'+')]
        key = [x.rstrip(b'\r') for x in lines]
        at = next((i for i in range(len(key) - len(old) + 1) if key[i:i + len(old)] == old), None)
        if at is None:
            if any(key[i:i + len(new)] == new for i in range(len(key) - len(new) + 1)):
                continue   # already applied
            raise RuntimeError(f'{patch.name} does not fit {target}')
        out, k = [], at
        for op, t in hunk:
            if op == b' ':
                out.append(lines[k]); k += 1
            elif op == b'-':
                k += 1
            else:
                out.append(t)
        lines = lines[:at] + out + lines[k:]
    target.write_bytes(b'\n'.join(lines))


def find_gxx():
    if os.environ.get('LIVE_CXX'):
        return os.environ['LIVE_CXX']
    p = shutil.which('g++')
    if p:
        # winget puts a link to g++ in ...\WinGet\Links; call the real file so g++ can find its own parts next to it
        return str(Path(p).resolve()) if IS_WIN else p
    if IS_WIN:
        la = Path(os.environ.get('LOCALAPPDATA', str(Path.home() / 'AppData' / 'Local')))
        cands = sorted(la.glob('Microsoft/WinGet/Packages/BrechtSanders.WinLibs*/mingw64/bin/g++.exe'))
        cands += [Path(r'C:\msys64\ucrt64\bin\g++.exe'),
                 Path(r'C:\msys64\mingw64\bin\g++.exe'), Path(r'C:\mingw64\bin\g++.exe'), Path(r'C:\w64devkit\bin\g++.exe')]
        for c in cands:
            if c.exists():
                return str(c)
    return None


GXX_HELP = ('g++ was not found. Install it, then restart live.py:\n'
            '  Windows: open "Terminal" and run   winget install BrechtSanders.WinLibs.POSIX.UCRT\n'
            '           (or install MSYS2 and run  pacman -S mingw-w64-ucrt-x86_64-gcc), then open a NEW terminal.\n'
            '  Linux / WSL: sudo apt install g++')


def load_cfg():
    cfg = json.loads((HARNESS / 'lcap_env17_wd.json').read_text(encoding='utf8'))
    return cfg.pop('_COMMON_ENV'), cfg


class Builder:
    def __init__(self, sim, work, jobs):
        self.sim, self.work, self.jobs = sim, work, jobs
        self.gxx = find_gxx()

    def sources(self):
        return sorted((self.sim / 'src').glob('*.cpp')) + sorted((self.sim / 'default_planner').glob('*.cpp'))

    def exe(self):
        return self.sim / 'build-live' / EXE

    def build(self, progress):
        """Recompile changed files only, then link. Returns (ok, message)."""
        if not self.gxx:
            return False, GXX_HELP
        sim = self.sim
        objd = sim / 'build-live' / 'obj'
        objd.mkdir(parents=True, exist_ok=True)
        hdr = max((p.stat().st_mtime for d in CODE_DIRS for p in (sim / d).rglob('*') if p.suffix in ('.h', '.hpp')), default=0)
        items = []
        for s in self.sources():
            rel = s.relative_to(sim).as_posix()
            o = objd / (rel.replace('/', '_') + '.o')
            items.append((rel, o, not o.exists() or o.stat().st_mtime < max(s.stat().st_mtime, hdr)))
        todo = [(rel, o) for rel, o, stale in items if stale]
        env = dict(os.environ)
        tmp = self.work / 'tmp'
        tmp.mkdir(exist_ok=True)
        env.update(TMP=str(tmp), TEMP=str(tmp), TMPDIR=str(tmp))

        def one(it):
            rel, o = it
            r = subprocess.run([self.gxx, *FLAGS, '-c', rel, '-o', o.relative_to(sim).as_posix()], cwd=sim, env=env,
                               capture_output=True, text=True, errors='replace')
            if r.returncode != 0 and o.exists():
                o.unlink()   # never link an old object of a file that no longer compiles
            return rel, r.returncode, r.stderr

        errors, done = [], 0
        progress(0, len(todo), '')
        if todo:
            with ThreadPoolExecutor(self.jobs) as ex:
                futs = [ex.submit(one, it) for it in todo]
                for f in as_completed(futs):
                    rel, rc, err = f.result()
                    done += 1
                    progress(done, len(todo), rel)
                    if rc != 0:
                        errors.append(f'---- {rel} ----\n{err.strip()}')
        if errors:
            return False, '\n\n'.join(errors)
        exe = self.exe()
        if todo or not exe.exists():
            progress(len(todo), len(todo), 'linking')
            args = [self.gxx, *[o.relative_to(sim).as_posix() for _, o, _ in items], '-o', exe.relative_to(sim).as_posix(), '-lpthread']
            if IS_WIN:
                args.append('-static')   # one self-contained .exe, no MinGW DLLs needed
            r = subprocess.run(args, cwd=sim, env=env, capture_output=True, text=True, errors='replace')
            if r.returncode != 0:
                return False, '---- linking ----\n' + r.stderr.strip()
        return True, f'compiled {len(todo)} file(s)' if todo else 'nothing to compile'


class Runner:
    KEYS = ('none', 'doorflow')

    def __init__(self, work):
        self.work, self.procs, self.meta = work, {}, {}
        self.lock = threading.Lock()
        old = [int(p.name[1:]) for p in (work / 'runs').glob('g*') if p.name[1:].isdigit()]
        self.gen = max(old, default=0)   # continue the numbering of an earlier session in the same work folder

    def stop(self):
        for p in self.procs.values():
            if p.poll() is None:
                p.kill()
        for p in self.procs.values():
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass

    def start(self, exe, settings, why):
        common, cfg = load_cfg()
        inst_name = settings['instance']
        if inst_name not in cfg:
            raise ValueError(f'unknown instance "{inst_name}" (use room200, room250 or room300)')
        inst = cfg[inst_name]
        f = HARNESS / 'data' / inst['mapfile']
        tpl = json.loads(f.read_text(encoding='utf8'))
        data = self.work / 'data' / inst_name
        data.mkdir(parents=True, exist_ok=True)
        for k in ('mapFile', 'agentFile', 'taskFile'):
            src = f.parent / tpl[k]
            dst = data / src.name
            if not dst.exists():
                shutil.copy(src, dst)
            tpl[k] = f'../../../data/{inst_name}/{src.name}'   # relative to the run folder: runs/g<N>/<key>
        tpl['delayConfig']['seed'] = int(settings['seed'])
        tpl['teamSize'] = inst['team']
        env_df = dict(common)
        env_df.update(inst['env'])
        for k, v in (settings.get('overrides') or {}).items():
            if v is None:
                env_df.pop(k, None)
            else:
                env_df[k] = str(v)
        env_none = {k: v for k, v in env_df.items() if k not in NONE_OFF}
        with self.lock:
            self.stop()
            self.gen += 1
            base = self.work / 'runs' / f'g{self.gen}'
            procs, meta = {}, dict(gen=self.gen, why=why, started=time.time(), team=inst['team'], instance=inst_name,
                                   seed=int(settings['seed']), planner_seed=int(settings['planner_seed']),
                                   ticks=int(settings['ticks']), env={'none': env_none, 'doorflow': env_df},
                                   overrides=settings.get('overrides') or {}, dirs={}, t0={}, t1={})
            for key, env in (('none', env_none), ('doorflow', env_df)):
                d = base / key
                d.mkdir(parents=True, exist_ok=True)
                (d / 'prob.json').write_text(json.dumps(tpl), encoding='utf8')
                full = dict(os.environ)
                for k in NONE_OFF:
                    full.pop(k, None)
                full.update(env)
                full['ROBOT_PLANNER_SEED'] = str(meta['planner_seed'])
                full['ROBOT_DUMP_POS'] = 'pos.bin'
                with open(d / 'stderr.txt', 'w') as errf:
                    procs[key] = subprocess.Popen([str(exe), '-i', 'prob.json', '-o', 'out.json', '-s', str(meta['ticks']), *SIM_ARGS],
                                                  cwd=d, env=full, stdout=subprocess.DEVNULL, stderr=errf)
                meta['dirs'][key] = d
                meta['t0'][key] = time.time()
            self.procs, self.meta = procs, meta
        for old in (self.work / 'runs').glob('g*'):   # keep the last three runs on disk
            if old.name[1:].isdigit() and int(old.name[1:]) <= self.gen - 3:
                shutil.rmtree(old, ignore_errors=True)

    def record_size(self):
        return 12 + 6 * self.meta['team']

    def status(self):
        with self.lock:
            if not self.meta:
                return None
            m, out = self.meta, {}
            for key in self.KEYS:
                p, d = self.procs[key], m['dirs'][key]
                try:
                    size = (d / 'pos.bin').stat().st_size
                except OSError:
                    size = 0
                rc = p.poll()
                if rc is not None and key not in m['t1']:
                    m['t1'][key] = time.time()
                r = dict(frames=size // self.record_size(), done=rc is not None, rc=rc,
                         seconds=round(m['t1'].get(key, time.time()) - m['t0'][key], 1))
                if rc is not None:
                    try:
                        r['finished'] = json.loads((d / 'out.json').read_text())['numTaskFinished']
                    except Exception:
                        r['finished'] = None
                    if rc != 0:
                        try:
                            r['stderr'] = (d / 'stderr.txt').read_text(errors='replace')[-3000:]
                        except OSError:
                            r['stderr'] = ''
                out[key] = r
            return dict(gen=m['gen'], why=m['why'], started=m['started'], team=m['team'], instance=m['instance'], seed=m['seed'],
                        planner_seed=m['planner_seed'], ticks=m['ticks'], env=m['env'], overrides=m['overrides'], runs=out)

    def read(self, gen, key, off, limit=6_000_000):
        with self.lock:
            if not self.meta or gen != self.meta['gen'] or key not in self.KEYS:
                return None
            path, rec = self.meta['dirs'][key] / 'pos.bin', self.record_size()
        if not path.exists():
            return b''
        with open(path, 'rb') as fh:
            fh.seek(off)
            buf = fh.read(limit)
        return buf[:len(buf) // rec * rec]


class Live:
    def __init__(self, work, jobs):
        self.work, self.sim, self.settings_file = work, work / 'sim', work / 'settings.json'
        self.builder, self.runner = Builder(self.sim, work, jobs), Runner(work)
        self.cond = threading.Condition()
        self.want_build, self.want_run, self.why = True, True, 'first start'
        self.state = dict(phase='starting', msg='', compiled=0, total=0, current='', errors='', built_at=None)
        self.history = deque(maxlen=12)

    # ---- setup ----
    def setup(self):
        self.work.mkdir(parents=True, exist_ok=True)
        if not (self.sim / 'src' / 'CompetitionSystem.cpp').exists():
            log(f'copying the simulator source to {self.sim}')
            shutil.copytree(SRC, self.sim, ignore=shutil.ignore_patterns('build*', '*.o', '__pycache__'))
            apply_patch(self.sim / 'src' / 'CompetitionSystem.cpp', PATCH)
        if not self.settings_file.exists():
            self.settings_file.write_text(json.dumps(DEFAULT_SETTINGS, indent=2, ensure_ascii=False), encoding='utf8')

    def load_settings(self):
        s = dict(DEFAULT_SETTINGS)
        s.update(json.loads(self.settings_file.read_text(encoding='utf8')))
        return s

    # ---- requests from the watcher and the page ----
    def request(self, build=False, run=True, why=''):
        with self.cond:
            self.want_build |= build
            self.want_run |= run
            self.why = why or self.why
            self.cond.notify()

    def set(self, **kw):
        self.state.update(kw)

    def worker(self):
        while True:
            with self.cond:
                while not (self.want_build or self.want_run):
                    self.cond.wait()
                build, run, why = self.want_build, self.want_run, self.why
                self.want_build = self.want_run = False
            if build:
                self.set(phase='building', msg=why, errors='', compiled=0, total=0, current='')
                log(f'building ({why})')
                t0 = time.time()
                ok, msg = self.builder.build(lambda d, n, c: self.set(compiled=d, total=n, current=c))
                if not ok:
                    self.set(phase='error', msg='compile error' if self.builder.gxx else 'g++ not found', errors=msg)
                    log('build failed:\n' + msg[:3000])
                    continue
                self.set(built_at=time.time())
                log(f'{msg} in {time.time() - t0:.0f} s')
            if run or build:
                try:
                    settings = self.load_settings()
                    self.runner.start(self.builder.exe(), settings, why)
                except (ValueError, KeyError, json.JSONDecodeError) as e:
                    self.set(phase='error', msg='settings.json problem', errors=f'{self.settings_file}:\n{e}')
                    log(f'settings problem: {e}')
                    continue
                self.history.appendleft(dict(gen=self.runner.gen, why=why, at=time.time()))
                self.set(phase='running', msg=why, errors='')
                log(f'run {self.runner.gen} started ({why})')

    def snapshot(self):
        snap = {}
        for d in CODE_DIRS:
            for p in (self.sim / d).rglob('*'):
                if p.suffix in CODE_EXT:
                    st = p.stat()
                    snap[p] = (st.st_mtime_ns, st.st_size)
        return snap

    def watcher(self):
        code = self.snapshot()
        sett = self.settings_file.stat().st_mtime_ns if self.settings_file.exists() else 0
        while True:
            time.sleep(0.5)
            try:
                now = self.snapshot()
                s2 = self.settings_file.stat().st_mtime_ns if self.settings_file.exists() else 0
            except OSError:
                continue   # a file is being replaced by the editor; look again next time
            changed = [p for p in now if code.get(p) != now[p]] + [p for p in code if p not in now]
            if changed or s2 != sett:
                time.sleep(0.4)   # let the editor finish writing
                try:
                    now = self.snapshot()
                    s2 = self.settings_file.stat().st_mtime_ns if self.settings_file.exists() else 0
                except OSError:
                    continue
                changed = [p for p in now if code.get(p) != now[p]] + [p for p in code if p not in now]
                names = sorted({p.relative_to(self.sim).as_posix() for p in changed})
                if names:
                    self.request(build=True, run=True, why=', '.join(names[:4]) + (' …' if len(names) > 4 else '') + ' changed')
                elif s2 != sett:
                    self.request(run=True, why='settings.json changed')
                code, sett = now, s2

    # ---- data for the page ----
    def static(self):
        _, cfg = load_cfg()
        try:
            inst = cfg[self.load_settings().get('instance', 'room250')]
        except (OSError, ValueError, KeyError):   # unreadable settings.json: the map is the same for all official instances
            inst = cfg['room250']
        f = HARNESS / 'data' / inst['mapfile']
        mapf = f.parent / json.loads(f.read_text(encoding='utf8'))['mapFile']
        lines = mapf.read_text().split('\n')
        rows = [l.rstrip('\r') for l in lines[lines.index('map') + 1:] if l.strip()]
        H, W = len(rows), len(rows[0])
        free = [1 if c in '.GSE' else 0 for r in rows for c in r[:W]]
        rg = json.loads(RG_FILE.read_text(encoding='utf8'))
        door_cells = {tuple(c) for d in rg['doors'] for c in d['cells']}
        lab = [-1] * (H * W)
        for room in rg['rooms']:
            r0, c0, r1, c1 = room['bbox']
            for r in range(r0, r1 + 1):
                for c in range(c0, c1 + 1):
                    if free[r * W + c] and (r, c) not in door_cells:
                        lab[r * W + c] = room['id']
        cell_doors = {}
        for j, d in enumerate(rg['doors']):   # cells within RADIUS steps (walking) of each door
            start = tuple(d['cells'][0])
            seen, q = {start: 0}, deque([start])
            while q:
                r, c = q.popleft()
                if seen[(r, c)] == RADIUS:
                    continue
                for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < H and 0 <= cc < W and free[rr * W + cc] and (rr, cc) not in seen:
                        seen[(rr, cc)] = seen[(r, c)] + 1
                        q.append((rr, cc))
            for r, c in seen:
                cell_doors.setdefault(r * W + c, []).append(j)
        ref = json.loads(REF_FILE.read_text()) if REF_FILE.exists() else None
        return dict(H=H, W=W, free=''.join(map(str, free)), lab=lab, cellDoors=cell_doors,
                    doors=[dict(id=d['id'], r=d['cells'][0][0], c=d['cells'][0][1], rooms=d['rooms']) for d in rg['doors']],
                    stuckTicks=STUCK_TICKS, radius=RADIUS, jamMin=JAM_MIN, ref=ref, refCond=REF)

    def status(self):
        s = dict(self.state)
        s.update(work=str(self.work), sim=str(self.sim), settings=str(self.settings_file), gxx=self.builder.gxx,
                 platform=sys.platform, history=list(self.history), run=self.runner.status())
        if s['phase'] == 'running' and s['run'] and all(r['done'] for r in s['run']['runs'].values()):
            s['phase'] = 'done'
        return s


LIVE = None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, body, ctype):
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, obj, code=200):
        self.send(code, json.dumps(obj, ensure_ascii=False).encode('utf8'), 'application/json; charset=utf-8')

    def do_GET(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        try:
            if u.path in ('/', '/index.html'):
                self.send(200, (HERE / 'live.html').read_bytes(), 'text/html; charset=utf-8')
            elif u.path == '/api/static':
                self.send_json(LIVE.static())
            elif u.path == '/api/status':
                self.send_json(LIVE.status())
            elif u.path == '/api/data':
                buf = LIVE.runner.read(int(q.get('gen', -1)), q.get('key', ''), int(q.get('off', 0)))
                if buf is None:
                    self.send(409, b'old run', 'text/plain')
                else:
                    self.send(200, buf, 'application/octet-stream')
            else:
                self.send(404, b'not found', 'text/plain')
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_POST(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        if u.path == '/api/rerun':
            LIVE.request(run=True, why='Rerun button')
            self.send_json(dict(ok=True))
        elif u.path == '/api/open':
            target = LIVE.sim if q.get('what') == 'code' else LIVE.settings_file
            try:
                if IS_WIN:
                    os.startfile(str(target))
                elif sys.platform == 'darwin':
                    subprocess.Popen(['open', str(target)])
                else:
                    subprocess.Popen(['xdg-open', str(target)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self.send_json(dict(ok=True))
            except Exception as e:
                self.send_json(dict(ok=False, error=str(e), path=str(target)))
        else:
            self.send(404, b'not found', 'text/plain')


def main():
    global LIVE
    ap = argparse.ArgumentParser(description='DoorFlow live: edit the simulator code, save, watch the new run.')
    ap.add_argument('--work', type=Path, default=default_work(), help='work folder (default: %(default)s)')
    ap.add_argument('--port', type=int, default=8765)
    ap.add_argument('--jobs', type=int, default=max(1, (os.cpu_count() or 2) - 1), help='parallel compile jobs')
    ap.add_argument('--no-browser', action='store_true')
    a = ap.parse_args()
    LIVE = Live(a.work.resolve(), a.jobs)
    LIVE.setup()
    server = None
    for port in range(a.port, a.port + 10):
        try:
            server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
            break
        except OSError:
            continue
    if server is None:
        sys.exit(f'ports {a.port}-{a.port + 9} are all busy; try --port 9000')
    url = f'http://127.0.0.1:{server.server_address[1]}/'
    print('\n  DoorFlow live is running.  Open:  ' + url)
    print(f'  Edit the code here:  {LIVE.sim}')
    print(f'  Settings:            {LIVE.settings_file}')
    print(f'  Compiler:            {LIVE.builder.gxx or "NOT FOUND (see the page)"}')
    print('  Stop with Ctrl+C.\n', flush=True)
    threading.Thread(target=LIVE.worker, daemon=True).start()
    threading.Thread(target=LIVE.watcher, daemon=True).start()
    if not a.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        LIVE.runner.stop()


if __name__ == '__main__':
    main()

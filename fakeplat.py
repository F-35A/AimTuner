"""Fake game + platform for tests (no Windows needed).

A wide textured world is panned horizontally by injected mouse counts, the
same way a first-person camera pans the screen. Optional static scope ring /
crosshair, accel and noise let tests check the probe's robustness."""
from __future__ import annotations

import numpy as np


def make_texture(h=900, w=6000, seed=1):
    rng = np.random.default_rng(seed)
    t = rng.normal(0, 1, (h // 6, w // 6)).astype(np.float32)
    t = np.kron(t, np.ones((6, 6), np.float32))  # blocky
    # blur a bit
    k = np.ones(5, np.float32) / 5
    t = np.apply_along_axis(lambda r: np.convolve(r, k, "same"), 1, t)
    t = np.apply_along_axis(lambda c: np.convolve(c, k, "same"), 0, t)
    t = (t - t.min()) / (t.max() - t.min()) * 200 + 20
    return t


class FakeGame:
    def __init__(self, pxpc=2.0, scope=False, accel=0.0, black=False, dead=False, seed=1):
        self.tex = make_texture(seed=seed)
        self.pxpc = pxpc
        self.x = 2000.0
        self.scope = scope
        self.accel = accel
        self.black = black
        self.dead = dead           # camera does not react (e.g. menu open)
        self.rect = (0, 0, 1280, 720)
        self.injected = []
        self.win = (8, True)
        self.raw_cb = None
        self.hot_cb = None

    # --- platform API
    def start(self, on_raw, on_hotkey):
        self.raw_cb, self.hot_cb = on_raw, on_hotkey

    def stop(self):
        pass

    def reregister(self):
        pass

    def cursor_pos(self):
        l, t, w, h = self.rect or (0, 0, 1280, 720)
        return getattr(self, "cursor", (l + w // 2, t + h // 2))

    def fg_process(self):
        return getattr(self, "fg", "RobloxPlayerBeta.exe")

    def inject(self, dx, dy):
        self.injected.append(dx)
        if self.dead:
            return
        gain = self.pxpc * (1 + self.accel * abs(dx) / 100)
        self.x += dx * gain
        if self.raw_cb:
            self.raw_cb(dx, dy, 0, 0)  # injected -> device 0

    def game_rect(self):
        return self.rect

    def grab(self, reg):
        l, t, w, h = reg
        if self.black:
            return np.zeros((h, w), np.float32)
        # world shifts left when camera turns right
        x0 = self.x + l
        i = int(np.floor(x0))
        f = x0 - i
        y0 = 100 + t // 4
        a = self.tex[y0:y0 + h, i:i + w + 1]
        img = a[:, :w] * (1 - f) + a[:, 1:w + 1] * f
        if self.scope:
            yy, xx = np.mgrid[0:h, 0:w]
            r = np.hypot(yy - h / 2, xx - w / 2)
            img = img.copy()
            img[r > min(h, w) * 0.48] = 0
            img[h // 2, :] = 0
            img[:, w // 2] = 0
        return img.astype(np.float32)

    def win_get(self):
        return self.win

    def win_set(self, speed, epp):
        self.win = (speed, epp)
        return True

    def overlay(self, on, hwnd=None, size=None, pos=(12, 12), alpha=225):
        self.ov = (on, size, pos, alpha)

    def screen_rect(self):
        return self.rect or (0, 0, 1920, 1080)

    def set_hotkeys(self, keys):
        self.keys = dict(keys)

    def beep(self, ok=True):
        pass


# ------------------------------------------------------------ fake PVP player
def _minjerk(n):
    s = np.linspace(0, 1, n + 1)
    pos = 10 * s**3 - 15 * s**4 + 6 * s**5
    return np.diff(pos)


class FakePlayer:
    """A player whose muscle memory is tuned to `ideal` sens. Playing at sens s, each
    flick's primary movement lands at (s/ideal)*(1+noise) of the target, then corrects."""

    def __init__(self, ideal_hip=1.0, ideal_ads=0.5, dpi=1600, seed=0, bias=-0.03, noise=0.08):
        self.ideal = {"hip": ideal_hip, "ads": ideal_ads}
        self.dpi = dpi
        self.rng = np.random.default_rng(seed)
        self.bias, self.noise = bias, noise

    def play(self, sens, n_flicks=120, ads_share=0.5, t0=0.0, look_share=0.0):
        """sens: {'hip': s, 'ads': s} (any units, same as ideal). -> raw events
        [(t, dx, dy, rmb, lmb)] at 1000 Hz, plus some tracking/spray noise."""
        r = self.rng
        ev = []
        t = t0
        rem = np.zeros(2)
        cpc = self.dpi / 2.54  # counts per cm

        def emit(vec_cm, dur, rmb, click_end=False):
            nonlocal t, rem
            n = max(2, int(dur * 1000))
            prof = _minjerk(n)
            for i in range(n):
                v = vec_cm * prof[i] * cpc + rem
                c = np.round(v)
                rem = v - c
                ev.append((t, int(c[0]), int(c[1]), rmb, 1 if (click_end and i == n - 1) else 0))
                t += 0.001

        def idle(dur, rmb):
            nonlocal t
            n = int(dur * 1000)
            for _ in range(n // 8):  # sparse zero events keep rmb state
                ev.append((t, 0, 0, rmb, 0))
                t += 0.008

        for _ in range(n_flicks):
            kind = "ads" if r.random() < ads_share else "hip"
            rmb = 1 if kind == "ads" else 0
            ang = r.uniform(0, 2 * np.pi)
            need = r.uniform(1.5, 8.0)              # cm of hand travel needed at ideal sens
            need_s = need * self.ideal[kind] / sens[kind]  # needed at actual sens
            prim = need * (1 + r.normal(self.bias, self.noise))  # muscle memory distance
            d = np.array([np.cos(ang), np.sin(ang)])
            idle(r.uniform(0.3, 0.9), rmb)
            if r.random() < look_share:
                # looking around: no target, random drift afterwards, no shot
                emit(d * prim, r.uniform(0.12, 0.22), rmb)
                idle(r.uniform(0.07, 0.12), rmb)
                emit(d * prim * r.uniform(0.05, 0.4), r.uniform(0.07, 0.12), rmb)
                idle(0.5, rmb)
                continue
            emit(d * prim, r.uniform(0.12, 0.22), rmb, click_end=abs(need_s - prim) <= 0.02)
            idle(r.uniform(0.07, 0.12), rmb)
            corr = need_s - prim
            if abs(corr) > 0.02:
                emit(d * corr, r.uniform(0.07, 0.12), rmb, click_end=True)
            if r.random() < 0.15:                    # a spray / tracking stretch
                idle(0.1, rmb)
                for _ in range(int(r.uniform(0.6, 1.2) * 1000)):
                    ev.append((t, int(r.normal(2, 2)), int(r.normal(0, 1)), rmb, 0))
                    t += 0.001
        idle(0.5, 0)
        return ev

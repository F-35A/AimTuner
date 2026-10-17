"""AimTuner — 게임 안에서 직접 재서 DPI·감도를 맞춰주는 세팅기.

1) DPI 버튼 단계별 실측  2) 게임 안에서 현재 감도 측정(F7/F8)
3) DPI 올리고, 게임 감도를 같은 손감각이 될 때까지 찾아줌  4) 전/후 비교
실행: python app.py   (pip install pygame numpy)
"""
from __future__ import annotations

import json
import os
import queue
import sys
import threading
import time

if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass

sys.setswitchinterval(0.001)  # input thread gets the GIL often; fewer late/lost events

import pygame  # noqa: E402

import core  # noqa: E402

import i18n  # noqa: E402
from i18n import T  # noqa: E402

IS_WIN = sys.platform == "win32"
W, H = 1180, 760
OV = (440, 156)          # overlay size in game mode
BG = (16, 19, 24)
PANEL = (27, 32, 40)
LINE = (52, 60, 72)
FG = (226, 230, 236)
DIM = (138, 148, 162)
ACC = (240, 176, 64)
GOOD = (96, 200, 128)
BAD = (232, 92, 84)

HK_HIP, HK_SCOPE, HK_TOGGLE = 1, 2, 3
HK_ID = {"hip": HK_HIP, "ads": HK_SCOPE, "toggle": HK_TOGGLE}
KEY_LABEL = {"toggle": T("큰 창 ↔ 작은 창"), "hip": T("일반 측정 / PVP 기록 시작·끝"), "ads": T("조준 측정")}
CORNERS = [("tl", T("왼쪽 위")), ("tr", T("오른쪽 위")), ("bl", T("왼쪽 아래")), ("br", T("오른쪽 아래"))]
ALPHAS = [140, 180, 225, 255]

DISCORD = "https://discord.gg/gfRYA7AqkR"
VERSION = "1.0.4"

STATE_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "AimTuner")
STATE_FILE = os.path.join(STATE_DIR, "state.json")


def find_font():
    for c in (r"C:\Windows\Fonts\malgun.ttf", r"C:\Windows\Fonts\segoeui.ttf",
              "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"):
        if os.path.exists(c):
            return c
    return pygame.font.match_font("malgungothic,notosanscjkkr,nanumgothic") or None


class Fonts:
    def __init__(self):
        self.p, self.c = find_font(), {}

    def __call__(self, size):
        if size not in self.c:
            self.c[size] = pygame.font.Font(self.p, size)
        return self.c[size]


class Button:
    def __init__(self, rect, text, cb, primary=False, enabled=True):
        self.r = pygame.Rect(rect)
        self.text, self.cb, self.primary, self.enabled = text, cb, primary, enabled

    def draw(self, s, F, mouse):
        hov = self.enabled and self.r.collidepoint(mouse)
        if self.primary:
            pygame.draw.rect(s, ACC if self.enabled else LINE, self.r, border_radius=6)
            if hov:
                pygame.draw.rect(s, FG, self.r, 2, border_radius=6)
            tc = BG if self.enabled else DIM
        else:
            pygame.draw.rect(s, (40, 47, 58) if hov else PANEL, self.r, border_radius=6)
            pygame.draw.rect(s, ACC if hov else LINE, self.r, 1, border_radius=6)
            tc = FG if self.enabled else DIM
        t = F(17).render(self.text, True, tc)
        s.blit(t, t.get_rect(center=self.r.center))

    def click(self, pos):
        if self.enabled and self.r.collidepoint(pos):
            self.cb()
            return True
        return False


class NumBox:
    def __init__(self, rect, value, label=""):
        self.r = pygame.Rect(rect)
        self.text, self.label, self.active = str(value), label, False

    def value(self, default=0.0):
        try:
            return float(self.text)
        except ValueError:
            return default

    def draw(self, s, F, mouse):
        if self.label:
            s.blit(F(14).render(self.label, True, DIM), (self.r.x, self.r.y - 21))
        pygame.draw.rect(s, (12, 14, 18), self.r, border_radius=5)
        pygame.draw.rect(s, ACC if self.active else LINE, self.r, 1, border_radius=5)
        t = F(17).render(self.text + ("|" if self.active and time.time() % 1 < .5 else ""), True, FG)
        s.blit(t, (self.r.x + 10, self.r.centery - t.get_height() // 2))

    def event(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.active = self.r.collidepoint(e.pos)
        elif self.active and e.type == pygame.TEXTINPUT and all(ch in "0123456789." for ch in e.text):
            self.text += e.text
        elif self.active and e.type == pygame.KEYDOWN:
            if e.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif e.key in (pygame.K_RETURN, pygame.K_TAB):
                self.active = False


class Check:
    def __init__(self, pos, text, value=False):
        self.r = pygame.Rect(pos[0], pos[1], 22, 22)
        self.text, self.value = text, value

    def draw(self, s, F, mouse):
        pygame.draw.rect(s, (12, 14, 18), self.r, border_radius=4)
        pygame.draw.rect(s, ACC if self.value else LINE, self.r, 1, border_radius=4)
        if self.value:
            pygame.draw.lines(s, ACC, False, [(self.r.x + 5, self.r.y + 11), (self.r.x + 10, self.r.y + 16),
                                              (self.r.x + 17, self.r.y + 6)], 3)
        s.blit(F(15).render(self.text, True, FG), (self.r.right + 10, self.r.y + 1))

    def event(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if pygame.Rect(self.r.x, self.r.y, 420, 24).collidepoint(e.pos):
                self.value = not self.value


def wrap(F, text, size, width):
    out, line = [], ""
    for word in text.split(" "):
        test = (line + " " + word).strip()
        if F(size).size(test)[0] > width and line:
            out.append(line)
            line = word
        else:
            line = test
    if line:
        out.append(line)
    return out


def make_platform():
    if IS_WIN:
        import win32
        return win32.Win32Platform()
    import fakeplat  # demo mode off Windows
    return fakeplat.FakeGame(pxpc=3.0)


class App:
    def __init__(self, pf=None):
        pygame.init()
        pygame.display.set_caption("AimTuner  ·  discord.gg/gfRYA7AqkR")
        try:
            base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
            pygame.display.set_icon(pygame.image.load(os.path.join(base, "icon.png")))
        except Exception:
            pass
        self.s = pygame.display.set_mode((W, H))
        self.F = Fonts()
        self.clock = pygame.time.Clock()
        self.running = True
        self.toast = ("", 0.0, FG)
        self.q = queue.Queue()
        self.user_counts = 0          # real-mouse counts, read by the probe thread
        self._ev_n, self._ev_t, self.poll_hz = 0, time.time(), 0.0
        self.probing = False
        self.overlay_on = False

        st = self.load()
        self.steps = [core.DpiStep.from_dict(d) for d in st.get("steps", [])]
        self.cur_idx = st.get("cur_idx", 0)
        self.new_idx = st.get("new_idx")
        self.A = {k: core.ProbeResult.from_dict(v) for k, v in st.get("A", {}).items() if k in ("hip", "scope")}
        self.A_idx = st.get("A_idx")
        self.B = {"hip": [], "scope": []}
        self.box_base = NumBox((40, 600, 150, 40), st.get("base_dpi", 800), T("1단계 DPI (마우스 스펙)"))
        g = st.get("game", {})
        self.box_vh = NumBox((40, 600, 150, 40), g.get("vh", ""), T("게임 일반 감도 값"))
        self.box_vs = NumBox((220, 600, 160, 40), g.get("vs", ""), T("조준 감도 값"))
        self.box_step = NumBox((420, 600, 110, 40), g.get("step", 0.01), T("감도 칸 단위"))
        self.box_min = NumBox((560, 600, 110, 40), g.get("min", 0.01), T("최솟값"))
        self.box_bh = NumBox((40, 600, 150, 40), "", T("지금 게임 일반 값"))
        self.box_bs = NumBox((210, 600, 150, 40), "", T("지금 게임 조준 값"))
        self.opt_rows = []
        pv = st.get("pvp", {})
        self.box_ph = NumBox((40, 200, 150, 40), pv.get("hip", g.get("vh", "")), T("일반 감도 (게임에 넣은 값)"))
        self.box_pa = NumBox((220, 200, 150, 40), pv.get("ads", g.get("vs", "")), T("조준 감도"))
        self.box_pstep = NumBox((400, 200, 110, 40), g.get("step", 0.01), T("감도 칸 단위"))
        self.chk_rel = Check((40, 262), T("조준 감도는 일반 감도에 곱해지는 방식"), pv.get("rel", True))
        self.pvp_hist = pv.get("hist", [])
        self.pvp_idx = pv.get("idx", self.cur_idx)
        self.rec = None              # list of events while recording
        self.rec_state = {"rmb": 0}
        self.rec_time = 0.0
        self.in_game = False
        self.locked = False          # cursor pinned to centre = aiming, not in a menu
        self._cur_prev = None
        self._cnt_prev = 0
        self._center = None
        self.menu_skipped = 0
        self.pvp_msg = []
        self._fg_t = 0
        o = st.get("ui", {})
        self.keys = dict(core.DEFAULT_KEYS)
        self.keys.update(o.get("keys", {}))
        if core.check_bindings(self.keys):
            self.keys = dict(core.DEFAULT_KEYS)
        self.ov_corner = o.get("corner", "tl")
        self.ov_alpha = o.get("alpha", 225)
        self.lang = o.get("lang", i18n.LANG)
        self.chk_auto = Check((60, 530), T("게임 화면이 앞에 오면 작은 창으로 자동 전환"), o.get("auto", True))
        self.capture = None          # action waiting for a new key
        self._auto_t = 0.0
        self._auto_want = None
        self.rec_shots = 0
        self.stage = "A"
        self.screen = "dpi"
        self.swipe = None
        self.game_msg = []

        self.pf = pf or make_platform()
        self.pf.start(self._raw_cb, lambda hid: self.q.put(("hot", hid)))
        if IS_WIN:
            try:
                self.pf.own_hwnd = pygame.display.get_wm_info()["window"]
            except Exception:
                pass
        self.win_speed, self.win_epp = self.pf.win_get()
        self.apply_keys()

    # ------------------------------------------------------------ keys / overlay
    def kn(self, act):
        return self.keys.get(act, "?")

    def apply_keys(self):
        kb = {}
        for act, spec in self.keys.items():
            pk = core.parse_key(spec)
            if pk and pk[0] == "kbd":
                kb[HK_ID[act]] = (pk[1], pk[2])
        try:
            self.pf.set_hotkeys(kb)
        except Exception:
            pass

    def set_key(self, act, spec):
        new = dict(self.keys)
        new[act] = spec
        errs = core.check_bindings(new)
        if errs:
            self.say(errs[0], BAD)
            return False
        self.keys = new
        self.apply_keys()
        self.save()
        self.say(f"{KEY_LABEL[act]} → {spec}", GOOD)
        return True

    # ------------------------------------------------------------ plumbing
    def _raw_cb(self, dx, dy, btn, dev, t=None):
        if dev:  # real device (injected moves have no device)
            self.user_counts += abs(dx) + abs(dy)
            if dx or dy:
                self._ev_n += 1
            rs = self.rec_state
            if btn & 0x0004:
                rs["rmb"] = 1
            if btn & 0x0008:
                rs["rmb"] = 0
            if btn & 0x0140:
                for act, spec in self.keys.items():
                    pk = core.parse_key(spec)
                    if pk and pk[0] == "mouse" and btn & pk[1]:
                        self.q.put(("hot", HK_ID[act]))
                if self.capture:
                    self.q.put(("cap", "MB4" if btn & 0x40 else "MB5"))
            rec = self.rec
            if rec is not None and self.in_game and self.locked and btn & 0x0001:
                self.rec_shots += 1
            if rec is not None and self.in_game and not self.locked:
                self.menu_skipped += 1
            if rec is not None and self.in_game and self.locked:
                rec.append((t if t is not None else time.perf_counter(), dx, dy, rs["rmb"], 1 if btn & 0x0001 else 0))
        self.q.put(("raw", dx, dy, btn, dev))

    def load(self):
        try:
            with open(STATE_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def save(self):
        try:
            os.makedirs(STATE_DIR, exist_ok=True)
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump({"steps": [x.to_dict() for x in self.steps], "cur_idx": self.cur_idx,
                           "new_idx": self.new_idx, "base_dpi": self.box_base.value(800),
                           "A": {k: v.to_dict() for k, v in self.A.items()}, "A_idx": self.A_idx,
                           "ui": {"keys": self.keys, "corner": self.ov_corner, "alpha": self.ov_alpha,
                                  "auto": self.chk_auto.value, "lang": self.lang},
                           "pvp": {"hip": self.box_ph.text, "ads": self.box_pa.text, "rel": self.chk_rel.value,
                                   "hist": self.pvp_hist, "idx": self.pvp_idx},
                           "game": {"vh": self.box_vh.text, "vs": self.box_vs.text,
                                    "step": self.box_step.text, "min": self.box_min.text}},
                          f, ensure_ascii=False, indent=1)
        except Exception:
            pass

    def say(self, msg, col=FG):
        self.toast = (msg, time.time() + 4, col)

    def grab(self, on):
        # Keep the cursor visible: grab + hidden cursor puts SDL in relative mode, which
        # takes over the process-wide raw-mouse registration and our counts stop.
        pygame.event.set_grab(on)
        pygame.mouse.set_visible(True)
        try:  # transparent cursor while swiping so it never covers the numbers
            if on:
                pygame.mouse.set_cursor((8, 8), (0, 0), (0,) * 8, (0,) * 8)
            else:
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
        except Exception:
            pass
        try:
            self.pf.reregister()
        except Exception:
            pass

    def text(self, t, pos, size=18, col=FG, anchor="topleft"):
        img = self.F(size).render(str(t), True, col)
        r = img.get_rect(**{anchor: pos})
        self.s.blit(img, r)
        return r

    def para(self, t, x, y, width, size=16, col=FG, gap=6):
        for ln in wrap(self.F, t, size, width):
            self.text(ln, (x, y), size, col)
            y += size + gap
        return y

    def go(self, sc):
        self.grab(False)
        self.swipe = None
        self.screen = sc

    # ------------------------------------------------------- swipe capture
    def start_swipe(self, done, expect=0):
        """Click = start (at the ruler's start mark), move LEFT without holding, click = stop.
        Only horizontal counts are used; vertical is ignored."""
        self.swipe = {"phase": "ready", "cnt": 0, "vert": 0, "t0": 0.0, "done": done,
                      "expect": expect, "last": None, "t_open": time.time()}
        self.grab(True)

    def _swipe_reset(self):
        sw = self.swipe
        sw.update(phase="ready", cnt=0, vert=0)

    def _swipe_start(self):
        sw = self.swipe
        sw.update(phase="arm", cnt=0, vert=0, t0=time.time(), last_move=time.time())

    def _swipe_stop(self):
        sw = self.swipe
        c = int(round(sw["cnt"]))
        if c < -40:
            self.say(T("오른쪽으로 움직였습니다. 왼쪽으로 밀어주세요."), BAD)
        elif c < 40:
            self.say(T("너무 짧습니다. 도착선까지 옮기세요."), BAD)
        else:
            sw["last"] = c
            self._swipe_reset()
            sw["done"](c)
            return
        self._swipe_reset()

    def swipe_raw(self, dx, dy, btn, dev):
        sw = self.swipe
        if not sw or not dev:
            return
        ph = sw["phase"]
        if ph == "ready":
            # click at the start mark (ignore the click that opened this screen)
            if btn & 0x0001 and time.time() - sw["t_open"] > 0.35:
                self._swipe_start()
            return
        sw["cnt"] -= dx                 # leftward = positive
        sw["vert"] += abs(dy)
        if abs(dx) >= 2 or abs(dy) >= 2:  # real motion (ignore 1-count sensor jitter)
            sw["last_move"] = time.time()
        if ph == "arm":
            if btn & 0x0002:            # start click released -> now moving freely
                sw["phase"] = "run"
            return
        if btn & 0x0001:                # a click still ends it manually
            self._swipe_stop()

    def swipe_tick(self):
        """Auto-finish: the hand has travelled and then stopped (hit the pad edge)."""
        sw = self.swipe
        if (sw and sw["phase"] == "run" and abs(sw["cnt"]) >= core.MIN_SWIPE
                and time.time() - sw.get("last_move", time.time()) >= core.STOP_HOLD_S):
            self._swipe_stop()

    def swipe_key(self, e):
        """Space works like the click (start / stop)."""
        sw = self.swipe
        if not sw or e.key != pygame.K_SPACE:
            return False
        if sw["phase"] == "ready":
            self._swipe_start()
            sw["phase"] = "run"
        elif sw["phase"] == "run":
            self._swipe_stop()
        return True

    def draw_swipe(self, y=250, ref_cm=None):
        """Movement indicator only. The finish is the END OF THE REAL RULER, never a point on
        screen: any on-screen finish line would have to assume a DPI, and stopping there
        would just return that assumed DPI."""
        sw = self.swipe
        if not sw:
            return
        x1, x0 = 120, W - 120
        moving = sw["phase"] in ("arm", "run")
        cnt = sw["cnt"] if moving else 0
        pygame.draw.line(self.s, LINE, (x1, y), (x0, y), 2)
        spacing, k = 48, 0.12                     # fixed px per count: same for every DPI
        off = (cnt * k) % spacing
        x = x1 + off
        while x < x0:                              # ticks scroll right as the mouse goes left
            pygame.draw.line(self.s, LINE, (int(x), y - 12), (int(x), y + 12), 2)
            x += spacing
        pygame.draw.circle(self.s, ACC if moving else DIM, (W // 2, y), 13)
        if sw["phase"] == "run" and abs(sw["cnt"]) >= core.MIN_SWIPE:
            held = min(1.0, (time.time() - sw.get("last_move", time.time())) / core.STOP_HOLD_S)
            if held > 0.05:
                pygame.draw.arc(self.s, GOOD, (W // 2 - 24, y - 24, 48, 48), 1.5708,
                                1.5708 + held * 6.2832, 4)
        pygame.draw.circle(self.s, BG, (W // 2, y), 5)
        big = f"{max(0, cnt):,.0f}" if moving else (f"{sw['last']:,}" if sw["last"] else "0")
        self.text(big, (W // 2, y - 110), 72, ACC if moving else FG, "center")
        if sw["phase"] == "ready":
            hint = T("마우스를 시작 지점(예: 패드 오른쪽 끝)에 대고 클릭 (또는 Space) → 시작")
        else:
            hint = T("버튼 누르지 말고 왼쪽으로 → 끝 지점에 닿아 멈추면 자동으로 끝")
        self.text(hint, (W // 2, y + 40), 19, FG if sw["phase"] == "ready" else ACC, "center")
        self.text(T("화면은 움직임 확인용입니다. 멈추는 기준은 화면이 아니라 손이 닿는 실제 지점입니다."),
                  (W // 2, y + 70), 15, DIM, "center")
        if moving and sw["vert"] > max(80, abs(sw["cnt"]) * 0.25):
            self.text(T("위아래로 많이 움직였습니다 — 자를 따라 수평으로"), (W // 2, y + 98), 15, BAD, "center")

    # ================================================================ DPI
    def btns_dpi(self):
        need_win = self.win_speed != 10 or self.win_epp
        return [Button((40, 676, 200, 46), T("+ DPI 단계 측정"), self.start_measure, primary=not self.steps),
                Button((254, 676, 150, 46), T("마지막 단계 삭제"), self.del_step, enabled=bool(self.steps)),
                Button((418, 676, 300, 46), T("윈도우 포인터 1:1 적용") if need_win else T("윈도우 포인터 OK"),
                       self.apply_win, enabled=need_win),
                Button((734, 676, 150, 46), T("PVP 튜닝 →"), self.to_pvp, enabled=len(self.steps) >= 1),
                Button((900, 676, 240, 46), T("게임에서 현재 감도 재기 →"), self.to_game_A,
                       primary=len(self.steps) >= 2, enabled=len(self.steps) >= 1)]

    def draw_dpi(self, mouse):
        self.text("AimTuner", (40, 26), 32, ACC)
        x = 220
        for i, lab in enumerate((T("1  DPI 단계 측정"), T("2  게임에서 현재 감도"), T("3  새 감도 찾기"),
                                 T("4  비교"))):
            x = self.text(lab, (x, 38), 17 if i else 18, FG if i == 0 else DIM).right + 26
        ws = T("윈도우 포인터 속도 {win_speed}/20 · 정확도 향상 {v}", win_speed=self.win_speed, v=T("켜짐") if self.win_epp else T("꺼짐"))
        bad = self.win_speed != 10 or self.win_epp
        self.text(ws + (T("  → 1:1(10, 끔) 권장. 게임 측정 전에 적용하세요.") if bad else ""), (40, 80), 15, BAD if bad else DIM)

        tbl = pygame.Rect(40, 112, 700, 440)
        pygame.draw.rect(self.s, PANEL, tbl, border_radius=8)
        for x, h in ((60, T("단계")), (190, T("실측 DPI")), (320, T("편차")), (410, T("떨림")), (500, T("상태"))):
            self.text(h, (x, 128), 14, DIM)
        pygame.draw.line(self.s, LINE, (56, 152), (724, 152))
        if not self.steps:
            self.para(T("마우스 DPI 버튼을 한 단계씩 돌리면서 단계마다 한 번씩 측정합니다. 지금 쓰는 단계도 포함해서 버튼이 지원하는 단계를 전부 재세요."), 60, 176, 640, 16, DIM)
        for i, st in enumerate(self.steps):
            y = 166 + i * 44
            pr = st.problems()
            self.text(st.label, (60, y), 18)
            self.text(f"{st.dpi:,.0f}", (190, y), 18)
            self.text(f"{st.cv*100:.1f}%", (320, y), 18, BAD if st.cv > core.MAX_CV else FG)
            self.text(f"{st.jitter:.1f}/s", (410, y), 18, BAD if st.jitter > core.MAX_JITTER_PER_SEC else FG)
            self.text("OK" if not pr else pr[0], (500, y + 2), 15, GOOD if not pr else BAD)
        if core.steps_look_identical(self.steps):
            self.para(T("모든 단계가 거의 같게 나왔습니다. 단계마다 DPI 버튼을 바꿨는지 확인하세요. 바꿨는데도 같다면 이 마우스의 버튼은 센서 DPI가 아니라 윈도우 커서 속도만 바꾸는 방식이라 게임에는 효과가 없습니다."),
                      60, 470, 640, 15, BAD)

        g = pygame.Rect(760, 112, 380, 440)
        pygame.draw.rect(self.s, PANEL, g, border_radius=8)
        self.text(T("어떻게 맞추나"), (780, 128), 19, ACC)
        y = self.para(T("낮은 DPI는 1카운트에 화면이 크게 돈다. 스코프에선 그 한 칸이 몇십 픽셀이라 그리드처럼 뚝뚝 끊긴다."),
                      780, 162, 340, 15)
        y = self.para(T("DPI를 올리고 게임 감도를 그만큼 내리면 손감각(마우스 1cm당 화면 이동)은 같고 한 칸만 작아진다."),
                      780, y + 10, 340, 15)
        y = self.para(T("게임 감도는 이 프로그램이 못 바꾼다. 대신 게임 안에서 {v}(일반)/{v2}(조준)을 누르면 화면이 실제로 얼마나 도는지 재서, 감도를 얼마나 올리고 내릴지 알려준다.", v=self.kn('hip'), v2=self.kn('ads')), 780, y + 10, 340, 15, DIM)
        self.para(T("자 필요 없음: 패드 끝↔끝처럼 손이 멈추는 고정된 두 지점 사이를 매번 똑같이 밀면 됩니다. 1단계 DPI만 스펙값을 넣으면 나머지는 비율로 계산됩니다."),
                  780, y + 10, 340, 15, DIM)
        self.box_base.draw(self.s, self.F, mouse)
        self.draw_footer(mouse, 732)

    def apply_win(self):
        ok = self.pf.win_set(10, False)
        self.win_speed, self.win_epp = self.pf.win_get()
        if self.A:
            self.A = {}
            self.say(T("윈도우 설정이 바뀌어 기존 게임 측정은 지웠습니다. 다시 재세요."), ACC)
        else:
            self.say(T("윈도우 포인터 1:1 적용됨") if ok else T("적용 실패"), GOOD if ok else BAD)
        self.save()

    def del_step(self):
        if self.steps:
            self.steps.pop()
            self.recalib()
            self.save()

    # ----------------------------------------------------------- calibrate
    def ref_cm(self):
        """Virtual reference length that makes step 1 equal the typed spec DPI."""
        base = self.box_base.value(800)
        if not self.steps or self.steps[0].counts <= 0 or base <= 0:
            return None
        return self.steps[0].counts / base * 2.54

    def recalib(self):
        r = self.ref_cm()
        if r:
            for st in self.steps:
                st.ref_cm = r

    def start_measure(self):
        self.measure = {"step": core.DpiStep(T("단계 {v}", v=len(self.steps)+1), ref_cm=self.ref_cm() or 0),
                        "phase": "swipe", "t0": 0, "still0": 0}
        self.screen = "measure"
        self.start_swipe(self._measured)

    def _measured(self, c):
        m = self.measure
        if c < core.MIN_SWIPE:
            self.say(T("너무 짧습니다. 끝 지점까지 쭉 밀어주세요."), BAD)
            return
        if self.steps and not core.ratio_plausible(c, self.steps[0].counts):
            self.say(T("1단계와 비교해 비정상적인 값입니다. 같은 두 지점 사이를 밀었는지 확인하고 다시."), BAD)
            return
        m["step"].swipes.append(c)
        if len(m["step"].swipes) >= 3:
            self.swipe = None
            m.update(phase="still", t0=time.time(), still0=self.user_counts)

    def draw_measure(self, mouse):
        m = self.measure
        st = m["step"]
        self.text(T("{label} 측정", label=st.label), (40, 28), 30, ACC)
        self.text(T("Esc: 취소"), (W - 40, 40), 15, DIM, "topright")
        if m["phase"] == "swipe":
            self.text(T("마우스 DPI 버튼으로 잴 단계를 맞추세요."), (40, 90), 20)
            self.text(T("매번 같은 두 지점 사이 (예: 패드 오른쪽 끝 → 왼쪽 끝)   [{v}/3]", v=len(st.swipes)), (40, 124), 20)
            if self.poll_hz > 0:
                self.text(T("마우스 입력 {hz:,.0f}Hz", hz=self.poll_hz), (W - 40, 124), 15, DIM, "topright")
            self.swipe["expect"] = st.counts if st.swipes else 0
            self.draw_swipe(300, st.ref_cm)
            base = self.box_base.value(800)
            for i, c in enumerate(st.swipes):
                if self.steps:
                    d = base * c / self.steps[0].counts
                    line = f"#{i+1}  {c:,} counts → {d:,.0f} DPI"
                else:
                    line = T("#{n}  {c:,} counts  (1단계 = {base:g} DPI 기준)", n=i + 1, c=c, base=base)
                self.text(line, (W // 2, 500 + i * 34), 21, FG, "center")
        elif m["phase"] == "still":
            left = 3 - (time.time() - m["t0"])
            still = self.user_counts - m["still0"]
            self.text(T("마우스에서 손 떼고 가만히"), (W // 2, 290), 30, FG, "center")
            self.text(f"{max(0, left):.1f}", (W // 2, 380), 76, ACC, "center")
            self.text(T("정지 중 카운트 {still}", still=still), (W // 2, 460), 18, DIM, "center")
            if left <= 0:
                st.jitter = still / 3.0
                m["phase"] = "done"
        else:
            pr = st.problems()
            self.text(T("실측 {dpi:,.0f} DPI", dpi=st.dpi), (W // 2, 250), 60, ACC, "center")
            self.text(T("편차 {v:.1f}% · 떨림 {jitter:.1f}/s", v=st.cv*100, jitter=st.jitter), (W // 2, 330), 21, FG, "center")
            self.text(T("문제 없음") if not pr else " / ".join(pr), (W // 2, 376), 19, GOOD if not pr else BAD, "center")
            self.text(T("Enter: 저장 · R: 다시 · Esc: 버리기"), (W // 2, 460), 19, DIM, "center")

    def measure_key(self, e):
        m = self.measure
        if e.key == pygame.K_ESCAPE:
            self.go("dpi")
        elif m["phase"] == "swipe" and e.key == pygame.K_BACKSPACE and m["step"].swipes:
            m["step"].swipes.pop()
        elif m["phase"] == "done" and e.key in (pygame.K_RETURN, pygame.K_SPACE):
            self.steps.append(m["step"])
            self.recalib()
            self.save()
            self.go("dpi")
        elif m["phase"] == "done" and e.key == pygame.K_r:
            self.start_measure()

    # ------------------------------------------------------- DPI check swipe
    def start_check(self, purpose):
        self.check = {"purpose": purpose, "res": None}
        self.screen = "check"
        self.start_swipe(self._checked)

    def _checked(self, c):
        idx, err = core.identify_step(c, self.steps)
        self.check["res"] = (idx, c)
        want = self.new_idx if self.check["purpose"] == "B" else None
        if idx is None:
            return
        if self.check["purpose"] == "A":
            self.cur_idx = idx
            self.save()
            self.go("game")
        elif self.check["purpose"] == "P":
            self.pvp_idx = self.cur_idx = idx
            self.save()
            self.go("pvp")
        elif idx == want:
            self.go("game")

    def draw_check(self, mouse):
        c = self.check
        if c["purpose"] in ("A", "P"):
            self.text(T("지금 쓰는 DPI 단계 확인"), (40, 28), 30, ACC)
            self.text(T("DPI 버튼은 평소 쓰는 그대로 두고, 자를 따라 한 번 재주세요."), (40, 96), 20)
        else:
            st = self.steps[self.new_idx]
            self.text(T("DPI 바꾸기"), (40, 28), 30, ACC)
            self.text(T("마우스 DPI 버튼을 [{label} · {dpi:,.0f}]로 바꾸고 자를 따라 한 번 재주세요.", label=st.label, dpi=st.dpi), (40, 96), 20)
        if self.swipe:
            want = self.steps[self.new_idx].counts if c["purpose"] == "B" else 0
            self.draw_swipe(300, self.steps[0].ref_cm if self.steps else 10)
            if want:
                self.swipe["expect"] = want
        if c["res"]:
            idx, cnt = c["res"]
            if idx is None:
                msg = T("{cnt:,} 카운트 — 측정해 둔 단계와 맞는 게 없습니다. 다시 그어보세요.", cnt=cnt)
            else:
                msg = T("{cnt:,} 카운트 — 지금은 [{label}]입니다. 버튼을 바꾸고 다시.", cnt=cnt, label=self.steps[idx].label)
            self.text(msg, (W // 2, 500), 21, BAD, "center")
        self.text(T("S: 확인 건너뛰기 · Esc: 뒤로"), (W // 2, 700), 15, DIM, "center")

    def check_key(self, e):
        back = {"A": "dpi", "B": "game", "P": "pvp"}[self.check["purpose"]]
        if e.key == pygame.K_ESCAPE:
            self.go(back)
        elif e.key == pygame.K_s:
            self.go("pvp" if back == "pvp" else "game")

    # =============================================================== GAME
    def to_game_A(self):
        self.stage = "A"
        self.start_check("A")

    # values typed by the user ------------------------------------------
    def grid(self):
        st = self.box_step.value(0.01) or 0.01
        return st, self.box_min.value(st) or st

    def a_value(self, kind):
        return (self.box_vh if kind == "hip" else self.box_vs).value(0)

    def options(self):
        if self.A_idx is None or self.a_value("hip") <= 0:
            return [], None
        step, vmin = self.grid()
        return core.plan_options(self.steps, self.A_idx, self.a_value("hip"), step, vmin)

    def to_stage_B(self):
        if not self.A.get("hip"):
            return
        if self.a_value("hip") <= 0:
            self.say(T("게임 일반 감도 값을 입력하세요 (지금 게임에 들어가 있는 숫자)."), BAD)
            return
        self.A_idx = self.cur_idx
        self.rec_notes = core.excluded_notes(self.steps)
        rows, best = self.options()
        if best is None:
            self.say(T("쓸 수 있는 DPI 단계가 없습니다."), BAD)
            return
        self.stage = "B"
        self.choose_option(rows[best])

    def choose_option(self, row):
        self.new_idx = row["idx"]
        self.B = {"hip": [], "scope": []}
        self.box_bh.text = f"{row['value']:g}"
        self.box_bs.text = self.box_vs.text  # scope: try unchanged first (often relative to hip)
        self.game_msg = []
        self.save()
        if self.new_idx != self.cur_idx:
            self.start_check("B")
        else:
            self.go("game")

    def on_hotkey(self, hid):
        if hid == HK_TOGGLE:
            self.set_overlay(not self.overlay_on)
            return
        if self.screen == "pvp":
            if hid == HK_HIP:
                self.rec_toggle()
            return
        if self.screen != "game" or self.probing:
            return
        kind = "hip" if hid == HK_HIP else "scope"
        self.probing = True
        self.game_msg = [(T("{v} 측정 중… 마우스 손 떼기", v=T("일반") if kind == 'hip' else T("조준")), ACC)]
        threading.Thread(target=self._probe_thread, args=(kind,), daemon=True).start()

    def _probe_thread(self, kind):
        base = self.user_counts
        try:
            r = core.probe(self.pf, user_moved=lambda: self.user_counts - base > 6)
            self.q.put(("probe", kind, r, None))
        except core.ProbeError as ex:
            self.q.put(("probe", kind, None, str(ex)))
        except Exception as ex:  # never kill the app
            self.q.put(("probe", kind, None, T("오류: {ex}", ex=ex)))

    def on_probe(self, kind, r, err):
        self.probing = False
        name = T("일반") if kind == "hip" else T("조준")
        if err:
            self.game_msg = [(f"{name}: {err}", BAD)]
            self.pf.beep(False)
            return
        warn = [] if r.linear else [(T("마우스 가속/스무딩 감지 — 게임 설정에서 꺼보세요."), BAD)]
        if self.stage == "A":
            self.A[kind] = r
            self.A_idx = self.cur_idx
            self.save()
            self.game_msg = [(T("{name} 기록: 한 칸 {pxpc:.2f}px", name=name, pxpc=r.pxpc), GOOD)] + warn
            self.pf.beep(True)
            return
        target = self.A.get(kind)
        box = self.box_bh if kind == "hip" else self.box_bs
        v_cur = box.value(0)
        if not target:
            self.game_msg = [(T("현재 세팅의 {name} 측정이 없어 비교할 수 없습니다.", name=name), ACC)]
            return
        m, _ = core.match(core.feel(target.pxpc, self.steps[self.A_idx].dpi), r.pxpc, self.steps[self.new_idx].dpi)
        if v_cur <= 0:
            txt, done = core.verdict(m, abs(m - 1) <= core.MATCH_TOL), abs(m - 1) <= core.MATCH_TOL
        else:
            pts = [(v, x.pxpc) for x, _, _, v in self.B[kind]] + [(v_cur, r.pxpc)]
            if kind == "hip" and self.a_value("hip") > 0:
                pts = [(self.a_value("hip"), target.pxpc)] + pts
            step, vmin = self.grid()
            tried = {round(v, 6): 1 / mm - 1 for _, mm, _, v in self.B[kind] if v > 0}
            txt, done, v_next = core.advise(v_cur, m, step, vmin, core.fit_k(pts), tried)
            box.text = f"{v_next:g}"
            if done:
                v_cur = v_next
        self.B[kind].append((r, m, done, v_cur))
        self.game_msg = [(f"{name}: {txt}", GOOD if done else ACC),
                         (T("한 칸 {pxpc:.2f}px → {pxpc2:.2f}px", pxpc=target.pxpc, pxpc2=r.pxpc), FG)] + warn
        self.pf.beep(done)

    def set_overlay(self, on):
        if on == self.overlay_on:
            return
        self.overlay_on = on
        if on:
            self.s = pygame.display.set_mode(OV)
        else:
            self.s = pygame.display.set_mode((W, H))
        self._place_overlay()

    def auto_overlay(self, now):
        """Game in front -> small HUD; our app in front again -> full window (with 0.6 s debounce)."""
        if not self.chk_auto.value or self.screen not in ("game", "pvp") or self.probing:
            self._auto_want = None
            return
        want = self.in_game
        if want != self._auto_want:
            self._auto_want, self._auto_t = want, now
            return
        if want != self.overlay_on and now - self._auto_t >= 0.6:
            self.set_overlay(want)

    def _place_overlay(self):
        try:
            hwnd = pygame.display.get_wm_info().get("window") if IS_WIN else None
            if self.overlay_on:
                pos = core.overlay_pos(self.ov_corner, self.pf.screen_rect(), OV)
                self.pf.overlay(True, hwnd, OV, pos, self.ov_alpha)
            else:
                self.pf.overlay(False, hwnd, (W, H))
        except Exception:
            pass

    def btns_game(self):
        if self.stage == "A":
            return [Button((40, 676, 140, 46), "← DPI", lambda: self.go("dpi")),
                    Button((560, 676, 280, 46), T("게임 모드 (작은 창, {v})", v=self.kn('toggle')), lambda: self.set_overlay(True)),
                    Button((860, 676, 280, 46), T("다음: 새 감도 찾기 →"), self.to_stage_B, primary=True,
                           enabled=bool(self.A.get("hip")))]
        done_hip = any(x[2] for x in self.B["hip"])
        return [Button((40, 676, 230, 46), T("← 현재 감도 다시"), self.to_game_A),
                Button((286, 676, 160, 46), T("DPI 다시 확인"), lambda: self.start_check("B")),
                Button((560, 676, 280, 46), T("게임 모드 (작은 창, {v})", v=self.kn('toggle')), lambda: self.set_overlay(True)),
                Button((860, 676, 280, 46), T("비교 보기 →"), lambda: self.go("result"), primary=done_hip,
                       enabled=bool(self.B["hip"]))]

    def game_boxes(self):
        if self.overlay_on or self.screen != "game":
            return []
        if self.stage == "A":
            return [self.box_vh, self.box_vs, self.box_step, self.box_min]
        return [self.box_bh, self.box_bs]

    def draw_game(self, mouse):
        y = 130
        if self.stage == "A":
            st = self.steps[self.cur_idx]
            self.text(T("2  게임에서 현재 감도 재기"), (40, 28), 28, ACC)
            self.text(T("지금 DPI: {label} · {dpi:,.0f}   (게임 감도는 평소 그대로)", label=st.label, dpi=st.dpi), (40, 80), 18)
            steps = [T("아래에 지금 게임 감도 숫자를 넣고, 게임 감도 칸이 몇 단위로 움직이는지(0.01, 0.05 …) 적으세요."),
                     T("게임 켜고 1인칭으로 무늬 있는 벽/지형을 보세요 (하늘·단색 X, 움직이는 사람 적은 곳)."),
                     T("마우스에서 손 떼고 {v} → 일반 감도 측정. 프로그램이 마우스를 살짝 좌우로 움직여 화면 회전을 잽니다.", v=self.kn('hip')),
                     T("우클릭 조준(ADS) 상태로 {v} → 조준 감도 측정.", v=self.kn('ads')),
                     T("{v}: 이 창 ↔ 게임 위 작은 창.", v=self.kn('toggle'))]
            for i, t in enumerate(steps):
                self.text(f"{i+1}.", (40, y), 17, ACC)
                y = self.para(t, 70, y, 640, 17) + 8
        else:
            st = self.steps[self.new_idx]
            self.text(T("3  새 감도 찾기"), (40, 28), 28, ACC)
            self.text(T("게임 칸 단위 {v:g}로 넣을 수 있는 조합 (클릭해서 바꾸기)", v=self.grid()[0]), (40, 80), 16, DIM)
            rows, best = self.options()
            self.opt_rows = []
            hdr = ((50, "DPI"), (170, T("일반 감도")), (300, T("손감각 오차")), (440, T("한 칸")))
            for x, h in hdr:
                self.text(h, (x, 108), 14, DIM)
            for j, rw in enumerate(rows[:5]):
                ry = 132 + j * 34
                rr = pygame.Rect(40, ry - 4, 660, 32)
                self.opt_rows.append((rr, rw))
                sel = rw["idx"] == self.new_idx
                if rr.collidepoint(mouse):
                    pygame.draw.rect(self.s, (36, 43, 54), rr, border_radius=5)
                if sel:
                    pygame.draw.rect(self.s, ACC, rr, 1, border_radius=5)
                col = ACC if sel else FG
                self.text(f"{rw['dpi']:,.0f}" + (" ★" if j == best else ""), (50, ry), 17, col)
                self.text(f"{rw['value']:g}", (170, ry), 17, col)
                self.text(f"{rw['err']*100:+.1f}%", (300, ry), 17,
                          GOOD if abs(rw["err"]) <= core.MATCH_TOL else BAD)
                self.text(T("{v:.2f}배", v=1/rw['finer']) if rw["finer"] else "", (440, ry), 17, col)
            y = 132 + min(5, len(rows)) * 34 + 14
            sel = next((rw for _, rw in self.opt_rows if rw["idx"] == self.new_idx), None)
            lines = [T("DPI 버튼 → {label} ({dpi:,.0f}), 게임 일반 감도 → {v}. 1인칭에서 {v2}.", label=st.label, dpi=st.dpi, v=self.box_bh.text, v2=self.kn('hip')),
                     T("조준 감도는 일단 그대로 두고 조준한 채 {v}. 그대로 맞으면 조준 감도가 일반 감도에 곱해지는 방식입니다.", v=self.kn('ads')),
                     T("결과에 나온 값으로 바꾸고 다시 {v}/{v2} — '확정'이 뜰 때까지. 아래 칸 = 지금 게임에 넣은 값.", v=self.kn('hip'), v2=self.kn('ads'))]
            if sel and abs(sel["err"]) > 0.001:
                lines.append(T("마우스 소프트웨어로 DPI를 직접 넣을 수 있으면 {exact_dpi:,.0f}로 하면 오차 0%.", exact_dpi=sel['exact_dpi']))
            lines += getattr(self, "rec_notes", [])
            for t in lines:
                y = self.para("· " + t, 40, y, 670, 15) + 4

        box = pygame.Rect(740, 120, 400, 520)
        pygame.draw.rect(self.s, PANEL, box, border_radius=8)
        self.text(T("측정 결과"), (760, 136), 18, ACC)
        y = 172
        for k, nm in (("hip", T("일반 {v}", v=self.kn('hip'))), ("scope", T("조준 {v}", v=self.kn('ads')))):
            a = self.A.get(k)
            self.text(nm, (760, y), 16, DIM)
            self.text(T("현재 한 칸 {pxpc:.2f}px", pxpc=a.pxpc) if a else T("현재: 미측정"), (880, y), 16, FG if a else DIM)
            y += 26
            for r_, m, done, v in (self.B[k][-4:] if self.stage == "B" else []):
                self.text(f"{v:g} → {r_.pxpc:.2f}px  {(1/m-1)*100:+.1f}%", (880, y), 15, GOOD if done else ACC)
                y += 22
            y += 14
        y += 10
        for msg, col in self.game_msg:
            y = self.para(msg, 760, y, 360, 17, col) + 4
        if IS_WIN and hasattr(self.pf, "hotkey_ok") and not all(self.pf.hotkey_ok.values() or [True]):
            self.para(T("단축키 등록 실패 — 다른 프로그램이 같은 키를 쓰는 중. 설정에서 바꾸세요."), 760, 590, 360, 14, BAD)
        for b in self.game_boxes():
            b.draw(self.s, self.F, mouse)

    def draw_overlay(self):
        self.s.fill((10, 12, 16))
        pygame.draw.rect(self.s, ACC, (0, 0, OV[0], OV[1]), 1)
        if self.screen == "pvp":
            stage = (T("PVP 기록 중 {v}:{v2:02d}", v=int(self.rec_time)//60, v2=int(self.rec_time)%60) if self.rec is not None
                     else T("PVP 튜닝 · 기록 꺼짐"))
            if self.rec is not None:
                where = T("조준 중 — 기록") if self.in_game and self.locked else T("메뉴/다른 창 — 일시정지")
                msgs = [(T("사격 {rec_shots} · {where}", rec_shots=self.rec_shots, where=where), GOOD if self.in_game and self.locked else DIM),
                        (T("일반 {v} · 조준 {v2}", v=self.box_ph.text, v2=self.box_pa.text), FG)]
            else:
                msgs = self.pvp_msg or [(T("일반 {v} · 조준 {v2}", v=self.box_ph.text, v2=self.box_pa.text), FG)]
        else:
            stage = T("현재 감도 재기") if self.stage == "A" else T("새 감도 찾기 · DPI {dpi:,.0f}", dpi=self.steps[self.new_idx].dpi)
            msgs = self.game_msg or [(T("{v} 일반 · {v2} 조준 측정", v=self.kn('hip'), v2=self.kn('ads')), FG)]
        self.text("AimTuner · " + stage, (12, 8), 15, BAD if self.rec is not None else ACC)
        y = 34
        for msg, col in msgs[:3]:
            for ln in wrap(self.F, msg, 17, OV[0] - 24)[:2]:
                self.text(ln, (12, y), 17, col)
                y += 23
        foot = T("{v} 기록 시작/끝 · {v2} 창 열기", v=self.kn('hip'), v2=self.kn('toggle')) if self.screen == "pvp" else T("{v} 일반 · {v2} 조준 · {v3} 창 열기", v=self.kn('hip'), v2=self.kn('ads'), v3=self.kn('toggle'))
        self.text(foot, (12, OV[1] - 24), 13, DIM)

    # ============================================================= RESULT
    def draw_result(self, mouse):
        self.text(T("4  전/후 비교"), (40, 28), 28, ACC)
        a_dpi, b_dpi = self.steps[self.A_idx].dpi, self.steps[self.new_idx].dpi
        box = pygame.Rect(40, 90, 1100, 330)
        pygame.draw.rect(self.s, PANEL, box, border_radius=8)
        self.text(T("전 (현재)"), (520, 106), 17, DIM)
        self.text(T("후 (새 세팅)"), (780, 106), 17, ACC)
        self.text(T("차이"), (1010, 106), 17, DIM)

        def last(k):
            ok = [x for x in self.B[k] if x[2]]
            return (ok or self.B[k] or [None])[-1]
        for k in ("hip", "scope"):
            b = last(k)
            if b and b[3]:
                self.text(T("{v} 감도 값 → {v2:g}", v=T("일반") if k == 'hip' else T("조준"), v2=b[3]), (40, 430 + (k == 'scope') * 26), 18, ACC)
        rows = [(T("마우스 DPI"), f"{a_dpi:,.0f}", f"{b_dpi:,.0f}", "")]
        for k, nm in (("hip", T("일반")), ("scope", T("조준"))):
            a, b = self.A.get(k), last(k)
            if not a or not b:
                continue
            rb = b[0]
            fa, fb = core.feel(a.pxpc, a_dpi), core.feel(rb.pxpc, b_dpi)
            rows.append((T("{nm} 손감각 (px/cm)", nm=nm), f"{fa:.0f}", f"{fb:.0f}", f"{(fb/fa-1)*100:+.1f}%"))
            rows.append((T("{nm} 한 칸 점프", nm=nm), f"{a.pxpc:.2f}px", f"{rb.pxpc:.2f}px", T("{v:.1f}배 촘촘", v=a.pxpc/rb.pxpc)))
        for i, (k, x, y_, d) in enumerate(rows):
            yy = 146 + i * 44
            self.text(k, (64, yy), 18, DIM)
            self.text(x, (520, yy), 20)
            self.text(y_, (780, yy), 20, ACC)
            self.text(d, (1010, yy), 18, GOOD)
        hip_ok = any(x[2] for x in self.B["hip"])
        sc_ok = (not self.A.get("scope")) or any(x[2] for x in self.B["scope"])
        if hip_ok and sc_ok:
            v, c = T("완료. DPI 버튼은 [{label}]에 두고, 게임 감도는 위 값으로 쓰면 됩니다.", label=self.steps[self.new_idx].label), GOOD
        else:
            v, c = T("아직 '확정'이 안 나온 항목이 있습니다. 3단계에서 알려준 값으로 바꾸고 다시 재세요."), ACC
        y = self.para(v, 40, 490, 1100, 20, c)
        self.para(T("손감각이 같으니 금방 적응됩니다. 이제 PVP 몇 판으로 감도를 다듬으세요."), 40, y + 8, 1100, 15, DIM)

    def btns_result(self):
        return [Button((40, 676, 200, 46), T("← 새 감도 찾기"), lambda: self.go("game")),
                Button((640, 676, 240, 46), T("처음으로"), self.finish),
                Button((900, 676, 240, 46), T("PVP로 다듬기 →"), self.to_pvp, primary=True)]

    def finish(self):
        self.cur_idx = self.new_idx if self.new_idx is not None else self.cur_idx
        self.save()
        self.stage = "A"
        self.go("dpi")

    # ================================================================ PVP
    def to_pvp(self):
        # carry the values found in step 3 over, if any
        for kind, box, a_box, b_box in (("hip", self.box_ph, self.box_vh, self.box_bh),
                                         ("scope", self.box_pa, self.box_vs, self.box_bs)):
            done = [x for x in self.B.get(kind, []) if x[2] and x[3]]
            if done:
                box.text = f"{done[-1][3]:g}"
            elif not box.text.strip():
                box.text = (b_box.text if self.B.get("hip") else "") or a_box.text
        if self.new_idx is not None and any(x[2] for x in self.B.get("hip", [])):
            self.pvp_idx = self.new_idx
        else:
            self.pvp_idx = self.cur_idx
        self.box_pstep.text = self.box_step.text
        self.save()
        self.go("pvp")

    def pvp_values(self):
        return {"hip": self.box_ph.value(0), "ads": self.box_pa.value(0)}

    def rec_toggle(self):
        if self.rec is None:
            v = self.pvp_values()
            if v["hip"] <= 0 or v["ads"] <= 0:
                self.say(T("일반/조준 감도 값을 넣으세요 (게임에 들어간 숫자 그대로)."), BAD)
                return
            self.rec = []
            self.rec_time = 0.0
            self.menu_skipped = 0
            self.rec_shots = 0
            self.pvp_msg = [(T("기록 중 — Roblox 화면일 때만 기록. PVP 2~3판(오픈월드는 20~30분) 하고 {v}.", v=self.kn('hip')), ACC)]
        else:
            self.finish_session()

    def finish_session(self):
        ev, self.rec = self.rec, None
        dpi = self.steps[self.pvp_idx].dpi if self.steps else 0
        flicks = core.find_flicks(ev, dpi)
        st = core.summarize(flicks)
        vals = self.pvp_values()
        sess = {"values": vals, "stats": st, "dpi": dpi, "secs": round(self.rec_time),
                "when": time.strftime("%m-%d %H:%M")}
        if st["hip"]["n"] + st["ads"]["n"] == 0:
            self.pvp_msg = [(T("플릭이 하나도 없습니다. Roblox 화면에서 실제로 플레이했는지 확인하세요."), BAD)]
            return
        self.pvp_hist.append(sess)
        step = self.box_pstep.value(0.01) or 0.01
        hv, ht, hf = core.tune_suggest(self.pvp_hist, "hip", step, step)
        pre = hv / vals["hip"] if self.chk_rel.value and vals["hip"] else 1.0
        av, at, af = core.tune_suggest(self.pvp_hist, "ads", step, step, pre=pre)
        sess["next"] = {"hip": hv, "ads": av, "final": hf and af}
        self.box_ph.text, self.box_pa.text = f"{hv:g}", f"{av:g}"
        msgs = [(ht, GOOD if hf else ACC), (at, GOOD if af else ACC)]
        if hf and af:
            msgs.append((T("최종: 일반 {hv:g} · 조준 {av:g} · DPI {dpi:,.0f}", hv=hv, av=av, dpi=dpi), GOOD))
        else:
            msgs.append((T("게임에 위 값 넣고 다시 '기록 시작' → 2~3판."), FG))
        self.pvp_msg = msgs
        self.save()

    def btns_pvp(self):
        rec = self.rec is not None
        return [Button((40, 676, 140, 46), T("← 처음"), lambda: self.go("dpi"), enabled=not rec),
                Button((196, 676, 160, 46), T("DPI 확인"), lambda: self.start_check("P"), enabled=not rec),
                Button((372, 676, 170, 46), T("기록 지우기"), self.pvp_clear, enabled=not rec and bool(self.pvp_hist)),
                Button((560, 676, 280, 46), T("게임 모드 (작은 창, {v})", v=self.kn('toggle')), lambda: self.set_overlay(True)),
                Button((860, 676, 280, 46), T("기록 끝 · 분석") if rec else T("기록 시작"), self.rec_toggle, primary=True)]

    def pvp_clear(self):
        self.pvp_hist = []
        self.pvp_msg = []
        self.save()

    def pvp_boxes(self):
        if self.overlay_on or self.screen != "pvp" or self.rec is not None:
            return []
        return [self.box_ph, self.box_pa, self.box_pstep]

    def draw_pvp(self, mouse):
        self.text(T("5  PVP로 감도 다듬기"), (40, 28), 28, ACC)
        st = self.steps[self.pvp_idx] if self.steps else None
        self.text(f"DPI: {st.label} · {st.dpi:,.0f}" if st else T("DPI 미측정"), (40, 76), 17)
        self.para(T("플릭할 때 지나쳐서 되돌아오면(오버) 감도가 높은 것, 덜 가서 더 미는 일(언더)이 많으면 낮은 것. 우클릭 조준 중 플릭은 조준 감도로 따로 셉니다."), 40, 104, 660, 15, DIM)
        for b in self.pvp_boxes():
            b.draw(self.s, self.F, mouse)
        if self.rec is None:
            self.chk_rel.draw(self.s, self.F, mouse)
        else:
            self.text(T("기록 중 {v}:{v2:02d}", v=int(self.rec_time)//60, v2=int(self.rec_time)%60), (40, 200), 30, BAD)
            state = (T("조준 화면 — 기록 중") if self.in_game and self.locked else
                     T("메뉴/지도/인벤 — 일시정지") if self.in_game else T("Roblox 화면 아님 — 일시정지"))
            self.text(state, (40, 244), 17, GOOD if self.in_game and self.locked else DIM)
            self.text(T("이번 세트 감도: 일반 {v} · 조준 {v2}", v=self.box_ph.text, v2=self.box_pa.text), (40, 270), 16, DIM)
        y = 310
        for msg, col in self.pvp_msg:
            y = self.para(msg, 40, y, 660, 17, col) + 6

        box = pygame.Rect(740, 90, 400, 560)
        pygame.draw.rect(self.s, PANEL, box, border_radius=8)
        self.text(T("세트 기록"), (760, 104), 18, ACC)
        for x, h in ((760, T("일반")), (830, T("조준")), (900, T("사격 플릭")), (980, T("오버% 일반/조준"))):
            self.text(h, (x, 136), 13, DIM)
        yy = 158
        for sess in self.pvp_hist[-14:]:
            v, stt = sess["values"], sess["stats"]

            def pct(k):
                sh = stt[k]["share"]
                return "—" if sh is None else f"{sh*100:.0f}"

            def col(k):
                sh = stt[k]["share"]
                return DIM if sh is None else (GOOD if core.SHARE_LO <= sh <= core.SHARE_HI else ACC)
            self.text(f"{v['hip']:g}", (760, yy), 16)
            self.text(f"{v['ads']:g}", (830, yy), 16)
            self.text(f"{stt['hip']['n']}/{stt['ads']['n']}", (900, yy), 16, DIM)
            self.text(pct("hip"), (980, yy), 16, col("hip"))
            self.text(pct("ads"), (1040, yy), 16, col("ads"))
            yy += 28
        if not self.pvp_hist:
            self.para(T("아직 기록이 없습니다. 감도 넣고 '기록 시작' → PVP 2~3판 → '기록 끝'."), 760, 160, 360, 15, DIM)
        self.text(T("{v}: 게임 안에서 기록 시작/끝 · 적정 오버 {v2:.0f}~{v3:.0f}%", v=self.kn('hip'), v2=core.SHARE_LO*100, v3=core.SHARE_HI*100),
                  (760, 620), 13, DIM)

    # =========================================================== SETTINGS
    def open_discord(self):
        try:
            import webbrowser
            webbrowser.open(DISCORD)
        except Exception:
            pass

    def draw_footer(self, mouse, y=642):
        label = T("무료 배포 · 업데이트/문의: ") + DISCORD.replace("https://", "")
        r = self.text(label, (40, y), 14, DIM)
        r = self.text(f"  v{VERSION} · MIT", (r.right, y), 14, LINE)
        self.discord_rect = pygame.Rect(40, y - 2, r.right - 40, 20)
        if self.discord_rect.collidepoint(mouse):
            self.text(label, (40, y), 14, ACC)

    def draw_settings(self, mouse):
        self.text(T("설정"), (40, 28), 30, ACC)
        self.text(T("단축키 (게임 안에서도 작동, 키보드 조합키·마우스 옆버튼 MB4/MB5 가능)"), (40, 90), 17, DIM)
        self.key_rows = []
        for i, act in enumerate(("toggle", "hip", "ads")):
            y = 130 + i * 56
            self.text(KEY_LABEL[act], (60, y + 10), 18)
            r = pygame.Rect(400, y, 220, 42)
            self.key_rows.append((r, act))
            cap = self.capture == act
            pygame.draw.rect(self.s, (40, 47, 58) if r.collidepoint(mouse) else PANEL, r, border_radius=6)
            pygame.draw.rect(self.s, ACC if cap else LINE, r, 1, border_radius=6)
            self.text(T("키를 누르세요… (Esc 취소)") if cap else self.kn(act), r.center, 16 if cap else 19,
                      ACC if cap else FG, "center")
            ok = getattr(self.pf, "hotkey_ok", {}).get(HK_ID[act], True)
            if not ok:
                self.text(T("등록 실패 — 다른 프로그램이 사용 중"), (640, y + 12), 15, BAD)
        self.text(T("작은 창 (게임 위 오버레이)"), (40, 320), 17, DIM)
        self.ov_rows = []
        cn = dict(CORNERS)[self.ov_corner]
        lang = {"ko": "한국어", "en": "English"}[self.lang]
        for j, (label, val) in enumerate(((T("위치"), cn), (T("불투명도"), f"{round(self.ov_alpha / 255 * 100)}%"),
                                          ("언어 / Language", lang))):
            y = 356 + j * 52
            self.text(label, (60, y + 10), 18)
            r = pygame.Rect(400, y, 220, 42)
            self.ov_rows.append((r, label))
            pygame.draw.rect(self.s, (40, 47, 58) if r.collidepoint(mouse) else PANEL, r, border_radius=6)
            pygame.draw.rect(self.s, LINE, r, 1, border_radius=6)
            self.text(val + "  >", r.center, 18, FG, "center")
        if self.lang != i18n.LANG:
            self.text(T("다시 켜면 적용됩니다"), (640, 356 + 2 * 52 + 12), 15, ACC)
        self.chk_auto.draw(self.s, self.F, mouse)
        self.para(T("위치·불투명도는 클릭할 때마다 바뀝니다. 작은 창은 클릭이 통과돼서 게임 조작을 막지 않습니다. 다시 큰 창으로 오려면 단축키를 누르거나 이 프로그램으로 Alt+Tab."), 60, 576, 1000, 15, DIM)
        self.draw_footer(mouse, 732)

    def btns_settings(self):
        return [Button((40, 676, 140, 46), T("← 뒤로"), lambda: self.go(self._settings_back)),
                Button((200, 676, 200, 46), T("단축키 기본값"), self.reset_keys),
                Button((860, 676, 280, 46), T("작은 창 미리보기"), lambda: self.set_overlay(True))]

    def open_settings(self):
        self._settings_back = self.screen if self.screen in ("dpi", "game", "pvp", "result") else "dpi"
        self.capture = None
        self.go("settings")

    def reset_keys(self):
        self.keys = dict(core.DEFAULT_KEYS)
        self.apply_keys()
        self.save()
        self.say(T("기본 단축키로 되돌렸습니다"), GOOD)

    def settings_click(self, pos):
        for r, act in getattr(self, "key_rows", []):
            if r.collidepoint(pos):
                self.capture = act
                return True
        for r, label in getattr(self, "ov_rows", []):
            if r.collidepoint(pos):
                if label == "언어 / Language":
                    self.lang = "en" if self.lang == "ko" else "ko"
                elif label == T("위치"):
                    ids = [c for c, _ in CORNERS]
                    self.ov_corner = ids[(ids.index(self.ov_corner) + 1) % 4]
                else:
                    self.ov_alpha = ALPHAS[(ALPHAS.index(self.ov_alpha) + 1) % len(ALPHAS)] \
                        if self.ov_alpha in ALPHAS else 225
                self.save()
                if self.overlay_on:
                    self._place_overlay()
                return True
        return False

    def capture_key(self, e):
        if e.key == pygame.K_ESCAPE:
            self.capture = None
            return
        if e.key in (pygame.K_LCTRL, pygame.K_RCTRL, pygame.K_LALT, pygame.K_RALT,
                     pygame.K_LSHIFT, pygame.K_RSHIFT):
            return  # wait for the real key
        m = e.mod
        spec = core.spec_from_pygame(pygame.key.name(e.key), bool(m & pygame.KMOD_CTRL),
                                     bool(m & pygame.KMOD_ALT), bool(m & pygame.KMOD_SHIFT))
        if not spec:
            self.say(T("이 키는 쓸 수 없습니다. F키, 글자, 숫자, 넘패드, Insert/Home 등을 쓰세요."), BAD)
            return
        if self.set_key(self.capture, spec):
            self.capture = None

    # =============================================================== LOOP
    def buttons(self):
        extra = ([Button((W - 150, 24, 110, 36), T("설정"), self.open_settings)]
                 if self.screen in ("dpi", "game", "pvp", "result") and not self.overlay_on
                 and self.rec is None else [])
        return extra + {"dpi": self.btns_dpi, "game": self.btns_game, "result": self.btns_result,
                "pvp": self.btns_pvp, "settings": self.btns_settings}.get(
            self.screen, lambda: [])() if not self.overlay_on else []

    def handle(self, e):
        if e.type == pygame.QUIT:
            self.running = False
            return
        if self.screen == "settings" and self.capture and e.type == pygame.KEYDOWN:
            self.capture_key(e)
            return
        if not IS_WIN and e.type == pygame.KEYDOWN:  # Windows delivers these as global hotkeys
            m = e.mod
            spec = core.spec_from_pygame(pygame.key.name(e.key), bool(m & pygame.KMOD_CTRL),
                                         bool(m & pygame.KMOD_ALT), bool(m & pygame.KMOD_SHIFT))
            for act, b in self.keys.items():
                if spec and spec.upper() == b.upper():
                    self.on_hotkey(HK_ID[act])
                    return
        if self.overlay_on:
            return
        if e.type == pygame.KEYDOWN and self.screen in ("measure", "check") and self.swipe_key(e):
            return
        if e.type == pygame.KEYDOWN:
            if self.screen == "measure":
                self.measure_key(e)
                return
            if self.screen == "check":
                self.check_key(e)
                return
        if self.screen == "dpi":
            self.box_base.event(e)
            self.recalib()
        for bx in self.game_boxes() + self.pvp_boxes():
            bx.event(e)
        if self.screen == "pvp" and self.rec is None:
            self.chk_rel.event(e)
        if (self.screen in ("dpi", "settings") and e.type == pygame.MOUSEBUTTONDOWN and e.button == 1
                and getattr(self, "discord_rect", None) and self.discord_rect.collidepoint(e.pos)):
            self.open_discord()
            return
        if self.screen == "settings":
            self.chk_auto.event(e)
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.settings_click(e.pos):
                return
        if (self.screen == "game" and self.stage == "B" and e.type == pygame.MOUSEBUTTONDOWN
                and e.button == 1):
            for rr, rw in self.opt_rows:
                if rr.collidepoint(e.pos) and rw["idx"] != self.new_idx:
                    self.choose_option(rw)
                    return
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for b in self.buttons():
                if b.click(e.pos):
                    break

    def pump_queue(self):
        while True:
            try:
                item = self.q.get_nowait()
            except queue.Empty:
                return
            if item[0] == "raw":
                self.swipe_raw(*item[1:])
            elif item[0] == "hot":
                if not (self.screen == "settings" and self.capture):
                    self.on_hotkey(item[1])
            elif item[0] == "cap":
                if self.capture and self.set_key(self.capture, item[1]):
                    self.capture = None
            elif item[0] == "probe":
                self.on_probe(*item[1:])

    def frame(self):
        if self.overlay_on:
            self.draw_overlay()
        else:
            mouse = pygame.mouse.get_pos()
            self.s.fill(BG)
            {"dpi": self.draw_dpi, "measure": self.draw_measure, "check": self.draw_check,
             "game": self.draw_game, "result": self.draw_result, "pvp": self.draw_pvp,
             "settings": self.draw_settings}[self.screen](mouse)
            for b in self.buttons():
                b.draw(self.s, self.F, mouse)
            msg, until, col = self.toast
            if msg and time.time() < until:
                img = self.F(17).render(msg, True, col)
                r = img.get_rect(midbottom=(W // 2, H - 96))
                pygame.draw.rect(self.s, PANEL, r.inflate(30, 16), border_radius=6)
                self.s.blit(img, r)
        pygame.display.flip()

    def step(self, dt=None):
        now = time.time()
        if now - self._ev_t >= 0.5:  # events/s while the mouse moves = polling rate (roughly)
            hz = self._ev_n / (now - self._ev_t)
            if hz > 50:
                self.poll_hz = hz
            self._ev_n, self._ev_t = 0, now
        if now - self._fg_t > 0.5:
            self._fg_t = now
            try:
                self.in_game = "roblox" in self.pf.fg_process().lower()
                r = self.pf.game_rect() if self.in_game else None
                self._center = (r[0] + r[2] // 2, r[1] + r[3] // 2) if r else None
            except Exception:
                self.in_game = False
        try:
            pos = self.pf.cursor_pos()
        except Exception:
            pos = None
        moved = self.user_counts - self._cnt_prev
        self.locked = core.cursor_locked(self._cur_prev, pos, self._center, moved, self.locked)
        self._cur_prev, self._cnt_prev = pos, self.user_counts
        self.auto_overlay(now)
        if self.rec is not None and self.in_game and self.locked:
            self.rec_time += dt if dt is not None else 1 / 120
        for e in pygame.event.get():
            self.handle(e)
        self.pump_queue()
        self.swipe_tick()
        if self.running:
            self.frame()

    def run(self):
        dt = 0.0
        smoke = float(os.environ.get("AIMTUNER_SMOKE", "0") or 0)  # CI: quit after N s
        t_end = time.time() + smoke if smoke else None
        while self.running:
            self.step(dt)
            dt = self.clock.tick(120) / 1000
            if t_end and time.time() > t_end:
                for sc in ("dpi", "settings", "pvp"):
                    self.go(sc)
                    self.frame()
                print("SMOKE OK", self.win_speed, getattr(self.pf, "hotkey_ok", None), flush=True)
                self.running = False
        self.save()
        self.pf.stop()
        pygame.quit()


def main():
    try:
        App().run()
    except Exception:
        import traceback
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(os.path.join(STATE_DIR, "error.log"), "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + f"v{VERSION}\n" + traceback.format_exc() + "\n")
        raise


if __name__ == "__main__":
    main()

import os
import sys
import time

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["AIMTUNER_LANG"] = "ko"  # assertions below match Korean messages
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402
import pytest  # noqa: E402

import core  # noqa: E402
import fakeplat  # noqa: E402
import win32  # noqa: E402


@pytest.fixture(autouse=True)
def fast(monkeypatch):
    monkeypatch.setattr(core.time, "sleep", lambda s: None)


def step(label, counts, jitter=0.0, ref=10.0):
    return core.DpiStep(label, list(counts), jitter, ref)


# ------------------------------------------------------------------ calibration
def test_dpi_math_and_problems():
    s = step("a", [1575] * 3)
    assert abs(s.dpi - 400) < 1 and not s.problems()
    assert step("x", [1000, 1300, 900]).problems()
    assert step("x", [1575] * 3, jitter=10).problems()
    assert step("x", [25196] * 3).problems()
    assert step("x", [1575, 1575]).problems()


def test_recommend_step():
    steps = [step("400", [1575] * 3), step("800", [3150] * 3), step("1600", [6299] * 3),
             step("3200", [12598, 11000, 14200]), step("6400", [25196] * 3)]
    idx, notes = core.recommend_step(steps, 0)
    assert idx == 2 and sum("제외" in n for n in notes) == 2
    idx, notes = core.recommend_step(steps, 2)
    assert idx == 2 and any("이미" in n for n in notes)


def test_identify_step():
    steps = [step("400", [1575] * 3), step("1600", [6299] * 3)]
    assert core.identify_step(1600, steps)[0] == 0
    assert core.identify_step(6100, steps)[0] == 1
    assert core.identify_step(3000, steps)[0] is None


# ------------------------------------------------------------------ vision probe
def test_phase_corr_subpixel_and_static_overlay():
    tex = fakeplat.make_texture()
    a = tex[100:400, 1000:1300]
    for true in (5.0, 37.4, 120.25):
        i = int(true)
        f = true - i
        b = tex[100:400, 1000 - i - 1:1300 - i] if f else tex[100:400, 1000 - i:1300 - i]
        if f:
            b = b[:, 1:] * (1 - f) + b[:, :-1] * f
        # static crosshair on both frames
        a2, b2 = a.copy(), b.copy()
        a2[150, :] = b2[150, :] = 0
        a2[:, 150] = b2[:, 150] = 0
        dx, dy, conf = core.phase_corr(a2, b2)
        assert abs(dx - true) < 0.5 and abs(dy) < 0.5 and conf > core.MIN_CONF


def test_phase_corr_flat():
    z = np.zeros((100, 100), np.float32)
    assert core.phase_corr(z, z)[2] == 0


@pytest.mark.parametrize("pxpc,scope", [(2.0, False), (0.37, False), (12.2, True), (0.05, False), (40, True)])
def test_probe_accuracy(pxpc, scope):
    g = fakeplat.FakeGame(pxpc=pxpc, scope=scope)
    x0 = g.x
    r = core.probe(g)
    assert r.pxpc == pytest.approx(pxpc, rel=0.01)
    assert r.linear
    assert g.x == pytest.approx(x0)            # view returned to start
    assert sum(g.injected) == 0


def test_probe_detects_accel():
    assert not core.probe(fakeplat.FakeGame(pxpc=3, accel=0.3)).linear


@pytest.mark.parametrize("kw,needle", [(dict(black=True), "단색"), (dict(dead=True), "회전")])
def test_probe_errors(kw, needle):
    with pytest.raises(core.ProbeError, match=needle):
        core.probe(fakeplat.FakeGame(**kw))


def test_probe_aborts_when_user_moves():
    with pytest.raises(core.ProbeError, match="움직"):
        core.probe(fakeplat.FakeGame(), user_moved=lambda: True)


def test_probe_no_window():
    g = fakeplat.FakeGame()
    g.rect = None
    with pytest.raises(core.ProbeError, match="창"):
        core.probe(g)


def test_snap_and_plan():
    assert core.snap(0.2125, 0.01) == 0.21 and core.snap(0.001, 0.05) == 0.05
    steps = [step("400", [1575] * 3), step("800", [3150] * 3), step("1600", [6299] * 3), step("3200", [12598] * 3)]
    rows, best = core.plan_options(steps, 0, 0.85, 0.01)
    assert rows[best]["dpi"] == pytest.approx(1600, rel=0.01) and rows[best]["value"] == 0.21
    assert rows[0]["value"] == 0.11 and abs(rows[0]["err"]) > 0.02      # 3200 too coarse
    rows, best = core.plan_options(steps, 0, 0.1, 0.05)                    # floor 0.05
    assert rows[best]["dpi"] == pytest.approx(800, rel=0.01) and rows[best]["value"] == 0.05


def test_next_value_and_fit_k():
    assert core.next_value(0.85, 0.25, 0.01)[0] == 0.21
    v, r, done = core.next_value(0.21, 1.012, 0.01)
    assert done and v == 0.21                     # 0.22 would be worse
    assert core.fit_k([(0.85, 12), (0.21, 12 * (0.21 / 0.85) ** 2)]) == pytest.approx(2)
    assert core.fit_k([(0.5, 3)]) == 1.0
    assert core.advise(0.21, 1.012, 0.01)[1]
    # two neighbours, both ~2.4% off: no ping-pong, keep the better measured one
    txt, done, v = core.advise(0.43, 1 / 1.024, 0.01, k=2, tried={0.42: -0.012})
    assert done and v == 0.42
    txt, done, v = core.advise(0.21, 4.0, 0.01, k=2)
    assert not done and v == 0.42


def test_match():
    fa = core.feel(12.0, 400)
    m, ok = core.match(fa, 12.0, 1600)      # DPI x4, sens unchanged -> lower x0.25
    assert m == pytest.approx(0.25) and not ok
    m, ok = core.match(fa, 3.03, 1600)
    assert ok
    assert "내리기" in core.verdict(0.25, False) and "일치" in core.verdict(1, True)


def test_win32_struct_sizes_match_x64():
    assert win32.struct_sizes() == {"INPUT": 40, "RAWINPUTHEADER": 24, "RAWMOUSE": 24,
                                    "MSG": 48, "BITMAPINFOHEADER": 40}


# ---------------------------------------------------------------- UI end-to-end
def raw_swipe(g, counts, chunks=10, A=None):
    """New protocol: click (start), release, slide LEFT without buttons, click (stop)."""
    if A is not None and A.swipe:
        A.swipe["t_open"] -= 1                    # past the 'opening click' guard
    g.raw_cb(0, 0, 0x1, 99)
    g.raw_cb(0, 0, 0x2, 99)
    for i in range(chunks):
        c = counts // chunks + (counts % chunks if i == chunks - 1 else 0)
        g.raw_cb(-c, 3, 0, 99)                    # left, with a little vertical wobble
    g.raw_cb(0, 0, 0x1, 99)
    g.raw_cb(0, 0, 0x2, 99)


def wait_probe(A):
    t0 = time.time()
    import threading as _th
    ev = _th.Event()
    while A.probing and time.time() - t0 < 60:
        A.step()
        ev.wait(0.02)  # yield to the probe thread (time.sleep is patched out)
    A.step()


@pytest.mark.parametrize("K", [1.0, 2.0])
def test_ui_full_flow(monkeypatch, tmp_path, K):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    import importlib
    import pygame as pg
    import app as appmod
    importlib.reload(appmod)
    g = fakeplat.FakeGame(pxpc=12.0, seed=3)
    A = appmod.App(pf=g)
    assert A.win_speed == 8
    A.apply_win()
    assert g.win == (10, False) and A.win_speed == 10

    # calibrate 400 and 1600 (no ruler: step 1 spec = 400, step 2 from the ratio)
    A.box_base.text = "400"
    for counts in (1575, 6300):
        A.start_measure()
        for _ in range(3):
            raw_swipe(g, counts, A=A)
            A.step()
        assert A.measure["phase"] == "still"
        A.measure["t0"] -= 3.1
        A.step()
        assert A.measure["phase"] == "done"
        A.handle(pg.event.Event(pg.KEYDOWN, key=pg.K_RETURN, mod=0, unicode="\r", scancode=0))
        A.step()
        assert A.screen == "dpi"
    assert [round(s.dpi) for s in A.steps] == [400, 1600]

    # A: identify current DPI by a swipe, then measure in game
    A.to_game_A()
    A.step()
    raw_swipe(g, 1580, A=A)
    A.step()
    assert A.screen == "game" and A.cur_idx == 0
    A.box_vh.text, A.box_vs.text, A.box_step.text, A.box_min.text = "0.85", "1", "0.01", "0.01"
    game = {"vh": 0.85, "vs": 1.0, "k": K, "base": 12.0 / 0.85 ** K}

    def apply(scope=False):  # the fake game's camera follows the values "typed in game"
        hip = game["base"] * game["vh"] ** game["k"]
        g.scope = scope
        g.pxpc = hip * 2.5 * game["vs"] if scope else hip
    apply()
    A.on_hotkey(appmod.HK_HIP)
    wait_probe(A)
    assert A.A["hip"].pxpc == pytest.approx(12.0, rel=0.01)
    apply(scope=True)
    A.on_hotkey(appmod.HK_SCOPE)
    wait_probe(A)
    assert A.A["scope"].pxpc == pytest.approx(30.0, rel=0.01)

    # overlay toggle (F6)
    A.on_hotkey(appmod.HK_TOGGLE)
    A.step()
    assert A.overlay_on and A.s.get_size() == appmod.OV
    A.on_hotkey(appmod.HK_TOGGLE)
    A.step()
    assert not A.overlay_on

    # B: best reachable combo = 1600 DPI, value 0.21 (0.2125 is not on a 0.01 grid)
    A.to_stage_B()
    assert A.new_idx == 1 and A.screen == "check" and A.box_bh.text == "0.21"
    raw_swipe(g, 1575, A=A)          # forgot to press the DPI button
    A.step()
    assert A.screen == "check" and A.check["res"][0] == 0
    raw_swipe(g, 6290, A=A)
    A.step()
    assert A.screen == "game" and A.stage == "B"

    # follow the advice until the hip value is final
    for _ in range(6):
        game["vh"] = A.box_bh.value()
        apply()
        A.on_hotkey(appmod.HK_HIP)
        wait_probe(A)
        if A.B["hip"][-1][2]:
            break
    r, m, done, v = A.B["hip"][-1]
    assert done and len(A.B["hip"]) <= 4
    # final value is the closest one the 0.01 grid allows
    ideal = 0.85 * (400 / 1600) ** (1 / K)
    assert abs(A.box_bh.value() - ideal) <= 0.0051
    # scope: unchanged value first; scope here is relative to hip, so it is already right
    for _ in range(6):
        game["vs"] = A.box_bs.value()
        apply(scope=True)
        A.on_hotkey(appmod.HK_SCOPE)
        wait_probe(A)
        if A.B["scope"][-1][2]:
            break
    assert A.B["scope"][-1][2] and A.B["scope"][0][3] == 1.0

    # probe blocked while one runs; errors shown not crashed
    g.dead = True
    A.on_hotkey(appmod.HK_HIP)
    wait_probe(A)
    assert A.game_msg and A.game_msg[0][1] == appmod.BAD
    g.dead = False

    A.go("result")
    A.step()
    A.finish()
    assert A.cur_idx == 1 and A.screen == "dpi"
    assert (tmp_path / "AimTuner" / "state.json").exists()
    pg.quit()


# ------------------------------------------------------------------ PVP tuning
@pytest.mark.parametrize("s,expect", [(0.7, "under"), (1.0, "ok"), (1.4, "over")])
def test_flick_classification(s, expect):
    p = fakeplat.FakePlayer(ideal_hip=1.0, ideal_ads=0.5, seed=2)
    st = core.summarize(core.find_flicks(p.play({"hip": s, "ads": s * 0.5}), 1600))
    for k in ("hip", "ads"):
        assert 40 <= st[k]["n"] <= 80            # ~60 each, sprays skipped
        sh = st[k]["share"]
        if expect == "under":
            assert sh < core.SHARE_LO and core.tune_factor(st[k]) > 1.2
        elif expect == "over":
            assert sh > core.SHARE_HI and core.tune_factor(st[k]) < 0.85
        else:
            assert core.tune_factor(st[k]) == 1.0


@pytest.mark.parametrize("start,ideal,step", [(1.4, 1.0, 0.01), (0.6, 1.0, 0.05), (0.85, 0.31, 0.01)])
def test_tuning_converges(start, ideal, step):
    p = fakeplat.FakePlayer(ideal_hip=ideal, ideal_ads=ideal * 0.5, seed=4)
    hist, v = [], {"hip": start, "ads": start * 0.4}
    for _ in range(10):
        st = core.summarize(core.find_flicks(p.play(v), 1600))
        hist.append({"values": dict(v), "stats": st})
        res = {k: core.tune_suggest(hist, k, step, step) for k in ("hip", "ads")}
        if all(r[2] for r in res.values()):
            break
        v = {k: r[0] for k, r in res.items()}
    assert all(r[2] for r in res.values()), hist
    assert res["hip"][0] == pytest.approx(ideal, rel=0.08)
    assert res["ads"][0] == pytest.approx(ideal * 0.5, rel=0.12)


def test_tune_needs_enough_flicks():
    p = fakeplat.FakePlayer()
    st = core.summarize(core.find_flicks(p.play({"hip": 1.4, "ads": 0.7}, n_flicks=20), 1600))
    v, txt, final = core.tune_suggest([{"values": {"hip": 1.4, "ads": 0.7}, "stats": st}], "hip", 0.01)
    assert v == 1.4 and not final and "더" in txt


def test_relative_ads_compensation():
    st = {"hip": {"n": 60, "share": 0.4, "med_ratio": 0}, "ads": {"n": 60, "share": 0.4, "med_ratio": 0}}
    h = [{"values": {"hip": 1.0, "ads": 0.5}, "stats": st}]
    v, txt, final = core.tune_suggest(h, "ads", 0.01, pre=0.8)   # hip went down 20%
    assert v == pytest.approx(0.62) and not final


def test_ui_pvp(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    import importlib
    import app as appmod
    importlib.reload(appmod)
    import pygame as pg
    g = fakeplat.FakeGame()
    A = appmod.App(pf=g)
    A.steps = [core.DpiStep("1600", [6299] * 3)]
    A.cur_idx = 0
    A.to_pvp()
    assert A.screen == "pvp"
    A.box_ph.text, A.box_pa.text, A.box_pstep.text = "", "", "0.01"
    A.rec_toggle()
    assert A.rec is None                       # values required
    A.box_ph.text, A.box_pa.text = "1.4", "0.7"
    A.chk_rel.value = False
    player = fakeplat.FakePlayer(ideal_hip=1.0, ideal_ads=0.5)

    def play(vals, fg="RobloxPlayerBeta.exe"):
        g.fg = fg
        A._fg_t = 0
        A.step()
        A.rec_toggle()
        assert A.rec is not None
        g.raw_cb(30, 0, 0, 7, 0.0)               # move with cursor pinned at centre -> aiming
        A.step()
        rmb = 0
        for t, dx, dy, r, l in player.play(vals):
            btn = (0x4 if r and not rmb else 0) | (0x8 if rmb and not r else 0) | (0x1 if l else 0)
            rmb = r
            g.raw_cb(dx, dy, btn, 7, t)
        A.step()
        A.rec_toggle()

    A.on_hotkey(appmod.HK_HIP)                          # F7 toggles recording on the PVP page
    assert A.rec is not None
    A.on_hotkey(appmod.HK_HIP)
    assert A.rec is None
    play({"hip": 1.4, "ads": 0.7}, fg="chrome.exe")     # not in Roblox -> nothing recorded
    assert not A.pvp_hist and A.pvp_msg[0][1] == appmod.BAD
    for _ in range(10):
        vals = A.pvp_values()
        play(vals)
        if A.pvp_hist[-1]["next"]["final"]:
            break
    assert A.pvp_hist[-1]["next"]["final"]
    assert A.box_ph.value() == pytest.approx(1.0, rel=0.08)
    assert A.box_pa.value() == pytest.approx(0.5, rel=0.12)
    # open-world menu: cursor roams -> nothing recorded
    A.rec_toggle()
    g.cursor = (100, 100)
    g.raw_cb(30, 0, 0, 7, 0.0)
    A.step()
    assert not A.locked
    A.rec.clear()                                # (one frame of lag before the switch is fine)
    for t, dx, dy, r, l in player.play({"hip": 1.0, "ads": 0.5}, n_flicks=20):
        g.raw_cb(dx, dy, 0x1 if l else 0, 7, t)
    assert A.rec == [] and A.menu_skipped > 0
    A.rec = None
    del g.cursor
    A.on_hotkey(appmod.HK_TOGGLE)
    A.step()
    assert A.overlay_on
    A.on_hotkey(appmod.HK_TOGGLE)
    A.save()
    A2 = appmod.App(pf=fakeplat.FakeGame())
    assert len(A2.pvp_hist) == len(A.pvp_hist)          # history persists
    pg.quit()


def test_look_around_flicks_are_ignored():
    """Checking corners (no target, no shot) must not drag the verdict. Here every
    look-around 'corrects forward', which alone would read as 'sens too low'."""
    p = fakeplat.FakePlayer(ideal_hip=1.0, ideal_ads=0.5, seed=5)
    ev = p.play({"hip": 1.0, "ads": 0.5}, n_flicks=300, look_share=0.5)
    fl = core.find_flicks(ev, 1600)
    st = core.summarize(fl)
    for k in ("hip", "ads"):
        assert st[k]["shots_only"] and st[k]["n"] < st[k]["all"]
        assert core.tune_factor(st[k]) == 1.0
    # without the shot filter the same data would wrongly say "raise sens"
    noshot = core.summarize([dict(x, shot=False) for x in fl])
    assert core.tune_factor(noshot["hip"]) > 1.0


def test_cursor_locked():
    c = (640, 360)
    assert core.cursor_locked(c, c, c, 50, False)                    # mouse moves, cursor pinned
    assert not core.cursor_locked(c, (900, 300), c, 50, True)        # far from centre: menu
    assert not core.cursor_locked((630, 360), (650, 360), c, 50, True)  # roaming near centre
    assert core.cursor_locked(c, c, c, 0, True)                      # idle keeps state
    assert not core.cursor_locked(c, c, c, 0, False)
    assert core.cursor_locked(None, None, None, 50, True)            # unknown keeps state


# ------------------------------------------------------------- keys / overlay
def test_key_specs():
    assert core.parse_key("CTRL+F7") == ("kbd", 2, 0x76)
    assert core.parse_key("shift+alt+k") == ("kbd", 5, ord("K"))
    assert core.parse_key("MB5") == ("mouse", 0x100)
    assert core.parse_key("CTRL+MB4") is None and core.parse_key("F13") is None
    assert core.spec_from_pygame("[7]", ctrl=True) == "CTRL+NUM7"
    assert core.spec_from_pygame("page up") == "PGUP"
    assert core.spec_from_pygame("left ctrl") is None
    assert core.check_bindings(core.DEFAULT_KEYS) == []
    assert core.check_bindings({"a": "F7", "b": "f7"})
    for spec in ("F1", "CTRL+SHIFT+Z", "NUM0", "`", "MB4"):
        assert core.parse_key(spec)


def test_overlay_pos():
    scr = (0, 0, 1920, 1080)
    assert core.overlay_pos("tl", scr, (440, 156)) == (12, 12)
    assert core.overlay_pos("br", scr, (440, 156)) == (1920 - 452, 1080 - 168)
    assert core.overlay_pos("tr", (100, 50, 800, 600), (400, 100)) == (488, 62)


def test_ui_settings_and_auto_overlay(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    import importlib
    import app as appmod
    importlib.reload(appmod)
    import pygame as pg
    g = fakeplat.FakeGame()
    A = appmod.App(pf=g)
    assert g.keys == {1: (0, 0x76), 2: (0, 0x77), 3: (0, 0x75)}       # defaults registered
    A.open_settings()
    A.step()
    # rebind "hip" to Ctrl+K by pressing it
    A.settings_click(A.key_rows[1][0].center)
    assert A.capture == "hip"
    A.handle(pg.event.Event(pg.KEYDOWN, key=pg.K_LCTRL, mod=pg.KMOD_LCTRL, unicode="", scancode=0))
    assert A.capture == "hip"                                          # modifier alone waits
    A.handle(pg.event.Event(pg.KEYDOWN, key=pg.K_k, mod=pg.KMOD_LCTRL, unicode="k", scancode=0))
    assert A.capture is None and A.keys["hip"] == "CTRL+K"
    assert g.keys[1] == (2, ord("K"))
    # duplicate rejected
    A.settings_click(A.key_rows[2][0].center)
    A.handle(pg.event.Event(pg.KEYDOWN, key=pg.K_k, mod=pg.KMOD_LCTRL, unicode="k", scancode=0))
    assert A.keys["ads"] == "F8" and A.capture == "ads"
    # mouse side button
    g.raw_cb(0, 0, 0x0100, 7)
    A.step()
    assert A.keys["ads"] == "MB5" and 2 not in g.keys
    # MB5 now fires the 'ads' hotkey (on the game page)
    fired = []
    A.on_hotkey = lambda hid: fired.append(hid)
    A.go("dpi")
    g.raw_cb(0, 0, 0x0100, 7)
    A.step()
    assert fired == [appmod.HK_SCOPE]
    del A.on_hotkey
    # overlay corner / alpha cycle
    A.open_settings()
    A.step()
    A.settings_click(A.ov_rows[0][0].center)
    A.settings_click(A.ov_rows[1][0].center)
    assert A.ov_corner == "tr" and A.ov_alpha == 255
    # auto overlay: game page, game in front -> HUD; our app in front -> full window
    A.steps = [core.DpiStep("1600", [6299] * 3)]
    A.cur_idx = 0
    A.to_pvp()
    g.fg = "RobloxPlayerBeta.exe"
    for _ in range(3):
        A._fg_t = 0
        A.step()
        A._auto_t -= 1
    assert A.overlay_on and g.ov[0] and g.ov[2] == core.overlay_pos("tr", g.screen_rect(), appmod.OV)
    g.fg = "python.exe"
    for _ in range(3):
        A._fg_t = 0
        A.step()
        A._auto_t -= 1
    assert not A.overlay_on
    # settings persist
    A.save()
    B = appmod.App(pf=fakeplat.FakeGame())
    assert B.keys["hip"] == "CTRL+K" and B.ov_corner == "tr"
    pg.quit()


# ------------------------------------------------------------------- i18n
def _templates():
    import ast as _ast
    out = []
    for f in ("app.py", "core.py"):
        src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), f), encoding="utf-8").read()
        for n in _ast.walk(_ast.parse(src)):
            if isinstance(n, _ast.Call) and getattr(n.func, "id", None) == "T" and n.args \
                    and isinstance(n.args[0], _ast.Constant):
                out.append(n.args[0].value)
    return out


def test_every_ui_string_has_english():
    import string
    from lang_en import EN
    fmt = string.Formatter()
    missing = [t for t in _templates() if t not in EN]
    assert not missing, missing
    for k, v in EN.items():
        assert sorted(f for _, f, _, _ in fmt.parse(k) if f) == sorted(f for _, f, _, _ in fmt.parse(v) if f), k


def test_no_hangul_left_untranslated():
    """Every Korean literal in app/core must go through T() (docstrings/comments aside)."""
    import ast as _ast
    import re as _re
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for f in ("app.py", "core.py"):
        tree = _ast.parse(open(os.path.join(root, f), encoding="utf-8").read())
        inT, docs = set(), set()
        for n in _ast.walk(tree):
            if isinstance(n, _ast.Call) and getattr(n.func, "id", None) == "T":
                for a in n.args:
                    inT.add(id(a))
            if isinstance(n, (_ast.Module, _ast.FunctionDef, _ast.ClassDef)) and n.body \
                    and isinstance(n.body[0], _ast.Expr):
                docs.add(id(n.body[0].value))
        bad = [n.value for n in _ast.walk(tree) if isinstance(n, _ast.Constant) and isinstance(n.value, str)
               and _re.search("[가-힣]", n.value) and id(n) not in inT and id(n) not in docs
               and n.value != "언어 / Language" and n.value not in ("한국어",)]
        assert not bad, (f, bad[:5])


def test_english_ui_renders_everything(monkeypatch, tmp_path):
    """Drive every screen in English; any bad format string would raise."""
    monkeypatch.setenv("APPDATA", str(tmp_path))
    import importlib
    import i18n
    monkeypatch.setattr(i18n, "LANG", "en")
    import app as appmod
    importlib.reload(appmod)
    import pygame as pg
    g = fakeplat.FakeGame(pxpc=12.0)
    A = appmod.App(pf=g)
    for c, j in ((1575, 0), (6300, 9), (6299, 0)):
        A.steps.append(core.DpiStep(f"S{len(A.steps)+1}", [c, c + 5, c - 5], j, 10))
    for sc in ("dpi", "settings"):
        A.go(sc)
        A.step()
    A.start_measure()
    A.step()
    A.measure["phase"] = "done"
    A.step()
    A.to_game_A()
    raw_swipe(g, 1578, A=A)
    A.step()
    A.box_vh.text, A.box_vs.text = "0.85", "0.5"
    A.on_hotkey(appmod.HK_HIP)
    wait_probe(A)
    g.scope = True
    A.on_hotkey(appmod.HK_SCOPE)
    wait_probe(A)
    A.to_stage_B()
    raw_swipe(g, 6299, A=A)
    A.step()
    g.scope, g.pxpc = False, 3.0
    A.on_hotkey(appmod.HK_HIP)
    wait_probe(A)
    assert "final" in A.game_msg[0][0] or "Set" in A.game_msg[0][0] or "Match" in A.game_msg[0][0]
    A.on_hotkey(appmod.HK_TOGGLE)
    A.step()
    A.on_hotkey(appmod.HK_TOGGLE)
    A.go("result")
    A.step()
    A.to_pvp()
    A.step()
    A.rec_toggle()
    A.step()
    A.rec_toggle()
    A.step()
    assert A.pvp_msg[0][0].startswith("No flicks")
    pg.quit()


# ------------------------------------------------------- raw input batch reading
def test_parse_raw_blocks():
    import ctypes
    def block(dx, dy, typ=0, extra=0, size=48):
        r = win32.RAWINPUT()
        r.header.dwType, r.header.dwSize, r.header.hDevice = typ, size, 5
        r.mouse.lLastX, r.mouse.lLastY, r.mouse.ulExtraInformation = dx, dy, extra
        b = bytes(r)[:size] + bytes(max(0, size - 48))
        return b + bytes((-len(b)) % 8)
    data = block(3, -2) + block(0, 0, typ=1, size=40) + block(7, 1, extra=win32.INJECT_TAG) + bytes(64)
    out = win32.parse_blocks(data, 3)
    assert [(r.mouse.lLastX, r.mouse.lLastY) for r in out] == [(3, -2), (7, 1)]   # keyboard block skipped
    assert out[1].mouse.ulExtraInformation == win32.INJECT_TAG
    assert win32.parse_blocks(data[:30], 3) == []                                  # truncated: no crash


def test_absurd_swipe_rejected(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    import importlib
    import app as appmod
    importlib.reload(appmod)
    import pygame as pg
    g = fakeplat.FakeGame()
    A = appmod.App(pf=g)
    A.box_base.text = "800"
    A.start_measure()
    raw_swipe(g, 150, A=A)            # mis-click length
    A.step()
    assert A.measure["step"].swipes == [] and A.toast[2] == appmod.BAD
    for _ in range(3):
        raw_swipe(g, 9449, A=A)       # pad edge to edge at 800
        A.step()
    A.measure["t0"] -= 4
    A.step()
    A.handle(pg.event.Event(pg.KEYDOWN, key=pg.K_RETURN, mod=0, unicode="\r", scancode=0))
    assert round(A.steps[0].dpi) == 800
    A.start_measure()
    raw_swipe(g, 394, A=A)            # 24x shorter than step 1 on the same distance: dropped input
    A.step()
    assert A.measure["step"].swipes == [] and A.toast[2] == appmod.BAD
    raw_swipe(g, 18898, A=A)          # same distance at 1600
    A.step()
    assert A.measure["step"].swipes == [18898]
    # typed spec changes every step proportionally
    A.box_base.text = "1000"
    A.recalib()
    assert round(A.steps[0].dpi) == 1000
    pg.quit()


# ------------------------------------------------------------- swipe protocol
def test_swipe_click_move_click(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    import importlib
    import app as appmod
    importlib.reload(appmod)
    import pygame as pg
    g = fakeplat.FakeGame()
    A = appmod.App(pf=g)
    A.box_base.text = "400"
    A.start_measure()
    g.raw_cb(0, 0, 0x1, 9)                    # the click that opened the screen: ignored
    A.step()
    assert A.swipe["phase"] == "ready"
    A.swipe["t_open"] -= 1
    g.raw_cb(0, 0, 0x1, 9)                    # start click
    A.step()
    assert A.swipe["phase"] == "arm"
    g.raw_cb(-100, 0, 0x2, 9)                 # release while already moving
    for _ in range(46):
        g.raw_cb(-100, 40, 0, 9)              # big vertical wobble is ignored
    g.raw_cb(-24, 0, 0, 9)
    A.step()
    assert A.swipe["phase"] == "run" and A.swipe["cnt"] == 4724
    g.raw_cb(0, 0, 0x1, 9)                    # stop click
    A.step()
    assert A.measure["step"].swipes == [4724] and A.swipe["phase"] == "ready"
    # moving right is rejected
    raw_swipe(g, -3000, A=A)
    A.step()
    assert A.measure["step"].swipes == [4724] and A.toast[2] == appmod.BAD
    # Space works as start/stop
    A.handle(pg.event.Event(pg.KEYDOWN, key=pg.K_SPACE, mod=0, unicode=" ", scancode=0))
    g.raw_cb(-4730, 0, 0, 9)
    A.step()
    A.handle(pg.event.Event(pg.KEYDOWN, key=pg.K_SPACE, mod=0, unicode=" ", scancode=0))
    assert A.measure["step"].swipes == [4724, 4730]
    # a mis-click-length swipe is refused
    raw_swipe(g, 150, A=A)
    A.step()
    assert len(A.measure["step"].swipes) == 2 and A.toast[2] == appmod.BAD
    A.frame()
    pg.quit()



def test_identical_steps_warning():
    assert core.steps_look_identical([step("a", [9449] * 3), step("b", [9500] * 3)])
    assert not core.steps_look_identical([step("a", [9449] * 3), step("b", [14173] * 3)])
    assert not core.steps_look_identical([step("a", [9449] * 3)])



def test_swipe_auto_stops_when_hand_stops(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    import importlib
    import app as appmod
    importlib.reload(appmod)
    import pygame as pg
    g = fakeplat.FakeGame()
    A = appmod.App(pf=g)
    A.start_measure()
    A.swipe["t_open"] -= 1
    g.raw_cb(0, 0, 0x1, 9)
    g.raw_cb(0, 0, 0x2, 9)
    A.step()
    A.swipe["last_move"] -= 5            # standing still before moving: must NOT finish
    A.step()
    assert A.swipe["phase"] == "run"
    for _ in range(40):
        g.raw_cb(-100, 0, 0, 9)
    A.step()
    assert A.swipe["phase"] == "run"     # still moving
    g.raw_cb(1, 0, 0, 9)                 # 1-count jitter at rest doesn't count as motion
    A.step()
    A.swipe["last_move"] -= core.STOP_HOLD_S + 0.01
    A.step()
    assert A.measure["step"].swipes == [3999]
    A.frame()
    pg.quit()

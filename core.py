"""AimTuner core: DPI calibration math, in-game sensitivity probe, matching.

Platform independent. Everything that touches Windows lives in win32.py.
"""
from __future__ import annotations

import statistics
import time
from dataclasses import dataclass, field

import numpy as np

from i18n import T  # noqa: E402

# Windows "pointer speed" slider (1..20) -> cursor multiplier. 10 (= 6/11) is 1:1.
WIN_SPEED_MULT = [0, 1/32, 1/16, 1/8, 2/8, 3/8, 4/8, 5/8, 6/8, 7/8, 1.0,
                  1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 3.0, 3.25, 3.5]

MAX_GOOD_DPI = 3200       # above this many sensors add smoothing/jitter
MAX_CV = 0.05             # calibration spread allowed (5%)
MAX_JITTER_PER_SEC = 3.0  # counts/sec while the mouse is resting
MATCH_TOL = 0.02          # 2% = same feel


def win_mult(speed: int) -> float:
    return WIN_SPEED_MULT[max(1, min(20, int(speed)))]


# ---------------------------------------------------------------- DPI steps
@dataclass
class DpiStep:
    label: str
    swipes: list = field(default_factory=list)  # counts per swipe
    jitter: float = 0.0                          # counts/sec at rest
    ref_cm: float = 10.0

    @property
    def counts(self) -> float:
        return statistics.median(self.swipes) if self.swipes else 0.0

    @property
    def dpi(self) -> float:
        if not self.swipes or self.ref_cm <= 0:
            return 0.0
        return self.counts / (self.ref_cm / 2.54)

    @property
    def cv(self) -> float:
        if len(self.swipes) < 2:
            return 0.0
        m = statistics.mean(self.swipes)
        return statistics.pstdev(self.swipes) / m if m else 1.0

    def problems(self) -> list[str]:
        p = []
        if len(self.swipes) < 3:
            p.append(T("측정 3회 미만"))
        if self.cv > MAX_CV:
            p.append(T("측정 편차 {v:.1f}%", v=self.cv*100))
        if self.jitter > MAX_JITTER_PER_SEC:
            p.append(T("정지 떨림 {jitter:.1f}/s", jitter=self.jitter))
        if self.dpi > MAX_GOOD_DPI:
            p.append(T("{MAX_GOOD_DPI} 초과(스무딩 위험)", MAX_GOOD_DPI=MAX_GOOD_DPI))
        return p

    def to_dict(self):
        return {"label": self.label, "swipes": self.swipes, "jitter": self.jitter, "ref_cm": self.ref_cm}

    @staticmethod
    def from_dict(d):
        return DpiStep(d["label"], list(d.get("swipes", [])), d.get("jitter", 0.0), d.get("ref_cm", 10.0))


def swipe_counts(dx: int, dy: int) -> float:
    return (dx * dx + dy * dy) ** 0.5


def excluded_notes(steps):
    return [T("[{label}] 제외: ", label=s.label) + ", ".join(s.problems()) for s in steps if s.dpi > 0 and s.problems()]


def recommend_step(steps: list[DpiStep], cur_idx: int):
    """Highest DPI step without problems. Returns (idx, notes)."""
    notes = excluded_notes(steps)
    good = [i for i, s in enumerate(steps) if s.dpi > 0 and not s.problems()]
    if not good:
        return cur_idx, notes + [T("문제없는 DPI 단계가 없습니다. 측정을 다시 해보세요.")]
    idx = max(good, key=lambda i: steps[i].dpi)
    if steps[idx].dpi <= steps[cur_idx].dpi * 1.05:
        notes.append(T("이미 쓸 수 있는 가장 높은 DPI입니다."))
    return idx, notes


# --------------------------------------------------------- phase correlation
def _hann2(h, w):
    return np.outer(np.hanning(h), np.hanning(w)).astype(np.float32)


def phase_corr(a: np.ndarray, b: np.ndarray, exclude_dx: float = 2.5):
    """Horizontal/vertical shift that maps a -> b (positive dx = content moved right).

    Peaks with |dx| <= exclude_dx are ignored so static HUD/scope rings/crosshair
    (which sit at shift 0) never win. Returns (dx, dy, confidence)."""
    a = a.astype(np.float32)
    b = b.astype(np.float32)
    if a.std() < 1.0 or b.std() < 1.0:
        return 0.0, 0.0, 0.0
    h, w = a.shape
    win = _hann2(h, w)
    A = np.fft.rfft2((a - a.mean()) * win)
    B = np.fft.rfft2((b - b.mean()) * win)
    R = B * np.conj(A)
    R /= np.abs(R) + 1e-6
    r = np.fft.irfft2(R, s=(h, w))
    r = np.fft.fftshift(r)
    cy, cx = h // 2, w // 2
    ex = int(np.ceil(exclude_dx))
    masked = r.copy()
    masked[:, cx - ex:cx + ex + 1] = -np.inf
    py, px = np.unravel_index(np.argmax(masked), r.shape)
    peak = r[py, px]
    finite = r[np.isfinite(r)]
    conf = float((peak - finite.mean()) / (finite.std() + 1e-9))

    def sub(m1, c0, p1):
        d = m1 - 2 * c0 + p1
        return 0.0 if abs(d) < 1e-12 else 0.5 * (m1 - p1) / d
    fx = sub(r[py, (px - 1) % w], peak, r[py, (px + 1) % w])
    fy = sub(r[(py - 1) % h, px], peak, r[(py + 1) % h, px])
    return float(px - cx + fx), float(py - cy + fy), conf


# ------------------------------------------------------------- in-game probe
class ProbeError(Exception):
    pass


@dataclass
class ProbeResult:
    pxpc: float            # screen pixels per mouse count (game sensitivity, as seen)
    linear: bool           # same px/count at two sizes -> no accel/smoothing
    spread: float          # relative spread of samples
    counts: int            # probe size used
    samples: list

    def to_dict(self):
        return {"pxpc": self.pxpc, "linear": self.linear, "spread": self.spread,
                "counts": self.counts, "samples": self.samples}

    @staticmethod
    def from_dict(d):
        return ProbeResult(d["pxpc"], d["linear"], d["spread"], d["counts"], d.get("samples", []))


MIN_CONF = 7.0
TARGET_PX = 80.0


def probe_region(rect):
    """Centre square of the game view; avoids HUD at the edges."""
    l, t, w, h = rect
    side = int(min(w, h) * 0.36)
    side = max(96, min(side, 384))
    return (l + (w - side) // 2, t + (h - side) // 2, side, side)


def probe(pf, settle=0.12, user_moved=lambda: False, log=lambda m: None):
    """Measure the game's px/count by injecting known mouse counts and watching the screen.

    pf: platform with inject(dx, dy), grab(region)->2D array, game_rect().
    Leaves the view where it started (every +S is followed by -S)."""
    rect = pf.game_rect()
    if not rect or rect[2] < 200 or rect[3] < 150:
        raise ProbeError(T("게임 창을 찾지 못했습니다. 게임 화면을 앞에 두고 누르세요."))
    reg = probe_region(rect)

    def one(S):
        a = pf.grab(reg)
        pf.inject(S, 0)
        time.sleep(settle)
        b = pf.grab(reg)
        pf.inject(-S, 0)
        time.sleep(settle)
        if user_moved():
            raise ProbeError(T("측정 중 마우스가 움직였습니다. 손을 떼고 다시 누르세요."))
        if a.std() < 1.0:
            raise ProbeError(T("화면이 단색/검정입니다. 무늬 있는 곳을 보거나 창 모드(테두리 없음)로 바꾸세요."))
        dx, dy, conf = phase_corr(a, b)
        return abs(dx), conf

    # 1) grow the probe from 1 count until the view moves ~TARGET_PX (never overshoot:
    #    a shift wider than the capture box gives a false peak)
    S = 1
    for _ in range(24):
        shift, conf = one(S)
        log(f"S={S} shift={shift:.1f}px conf={conf:.1f}")
        if conf < MIN_CONF or shift < 12:
            if S >= 4096:
                raise ProbeError(T("화면 회전이 감지되지 않습니다. 1인칭으로, 마우스가 카메라를 돌리는 상태에서 누르세요."))
            S *= 2
            continue
        if shift > reg[2] * 0.4:
            raise ProbeError(T("감도가 너무 높아 1카운트도 화면 밖으로 나갑니다."))
        S2 = max(S, int(round(S * TARGET_PX / shift)))
        if S2 > S:  # confirm the extrapolation actually lands where predicted
            sh2, cf2 = one(S2)
            log(f"S={S2} shift={sh2:.1f}px conf={cf2:.1f}")
            if cf2 < MIN_CONF or abs(sh2 / S2 - shift / S) > 0.25 * shift / S:
                raise ProbeError(T("화면 움직임이 일정하지 않습니다. 움직이는 물체 없는 곳에서 다시."))
        S = S2
        break
    else:
        raise ProbeError(T("측정 실패. 무늬가 많은 벽/지형을 보고 다시 시도하세요."))

    # 2) measure at S (x3) and S/4 (x2) for a linearity check (accel / smoothing)
    big, small = [], []
    for _ in range(3):
        sh, cf = one(S)
        if cf >= MIN_CONF:
            big.append(sh / S)
    half = max(1, S // 4)
    for _ in range(2):
        sh, cf = one(half)
        if cf >= MIN_CONF and sh >= 8:
            small.append(sh / half)
    if len(big) < 2:
        raise ProbeError(T("화면이 흔들려 측정이 불안정합니다. 움직이는 물체 없는 곳에서 다시."))
    pxpc = statistics.median(big)
    spread = (max(big) - min(big)) / pxpc if pxpc else 1
    linear = True
    if small:
        linear = abs(statistics.median(small) - pxpc) / pxpc < 0.04
    return ProbeResult(pxpc, linear, spread, S, [round(x, 5) for x in big + small])


# ---------------------------------------------------------------- matching
def feel(pxpc: float, dpi: float) -> float:
    """Hand feel = screen pixels per centimetre of mouse travel."""
    return pxpc * dpi / 2.54


def match(target_feel: float, pxpc: float, dpi: float):
    """How to change the in-game sensitivity so feel == target. Returns (multiplier, ok)."""
    cur = feel(pxpc, dpi)
    if cur <= 0:
        return 1.0, False
    m = target_feel / cur
    return m, abs(m - 1) <= MATCH_TOL


def verdict(m: float, ok: bool) -> str:
    if ok:
        return T("일치 — 이 감도로 확정")
    d = T("올리기") if m > 1 else T("내리기")
    return T("감도 ×{m:.3f} ({d})", m=m, d=d)


def identify_step(counts: float, steps: list[DpiStep], tol: float = 0.12):
    """Which calibrated step produced this swipe? -> (index or None, relative error)."""
    best, err = None, 9.0
    for i, s in enumerate(steps):
        if s.counts <= 0:
            continue
        e = abs(counts - s.counts) / s.counts
        if e < err:
            best, err = i, e
    return (best, err) if err <= tol else (None, err)


# ------------------------------------------------- quantized game sensitivity
# Games like BRM5 only accept values on a grid (0.01, 0.05 ...). Find the best
# reachable combination of DPI step + grid value instead of an exact multiplier.
def snap(v: float, step: float, vmin: float = 0.0) -> float:
    step = step if step > 0 else 0.01
    s = round(round(v / step) * step, 6)
    return max(s, vmin if vmin > 0 else step)


def plan_options(steps, a_idx, value, step, vmin=0.0, k=1.0):
    """For every usable DPI step: the closest reachable in-game value and its feel error.

    feel ~ dpi * value**k (k=1 for linear sliders). Returns rows sorted best-first and
    the index into rows of the recommendation (highest DPI within MATCH_TOL, else
    smallest error)."""
    a_dpi = steps[a_idx].dpi
    rows = []
    for i, s in enumerate(steps):
        if s.dpi <= 0 or (s.problems() and i != a_idx):
            continue
        ideal = value * (a_dpi / s.dpi) ** (1 / k)
        v = snap(ideal, step, vmin)
        err = (s.dpi * v ** k) / (a_dpi * value ** k) - 1
        rows.append({"idx": i, "dpi": s.dpi, "value": v, "ideal": ideal, "err": err,
                     "finer": s.dpi / a_dpi, "exact_dpi": a_dpi * (value / v) ** k})
    rows.sort(key=lambda r: -r["dpi"])
    ok = [j for j, r in enumerate(rows) if abs(r["err"]) <= MATCH_TOL]
    best = ok[0] if ok else min(range(len(rows)), key=lambda j: abs(rows[j]["err"])) if rows else None
    return rows, best


def fit_k(points):
    """points: [(value, pxpc)] measured at the same game state. Slider curve exponent:
    pxpc ~ value**k. Uses the two most recent distinct values; 1.0 if unknown."""
    pts = [(v, p) for v, p in points if v > 0 and p > 0]
    for i in range(len(pts) - 1, 0, -1):
        for j in range(i - 1, -1, -1):
            v1, p1 = pts[i]
            v2, p2 = pts[j]
            if abs(v1 - v2) / max(v1, v2) > 0.03:
                import math
                k = math.log(p1 / p2) / math.log(v1 / v2)
                return max(0.3, min(3.0, k))
    return 1.0


def next_value(v_cur, m, step, vmin=0.0, k=1.0):
    """Feel must change by factor m. Pick the grid value whose predicted feel is closest.

    Returns (value, predicted residual error, done). done=True when staying put is best,
    i.e. nothing on the grid gets closer."""
    ideal = v_cur * m ** (1 / k)
    base = snap(ideal, step, vmin)
    cands = {snap(base + d * step, step, vmin) for d in (-1, 0, 1)} | {round(v_cur, 6)}

    def resid(v):
        return m / (v / v_cur) ** k - 1
    best = min(cands, key=lambda v: (abs(resid(v)), abs(v - v_cur)))
    if abs(resid(best)) > abs(m - 1) - 0.003:   # hysteresis: don't hop for <0.3%
        best = round(v_cur, 6)
    return best, resid(best), abs(best - v_cur) < 1e-9


def advise(v_cur, m, step, vmin=0.0, k=1.0, tried=None):
    """Human text for the B loop. tried: {value: measured feel error} from earlier probes,
    so two neighbouring grid values never ping-pong; the better measured one wins."""
    if abs(m - 1) <= MATCH_TOL:
        return T("일치 ({v:+.1f}%) — {v_cur:g} 확정", v=(1/m-1)*100, v_cur=v_cur), True, v_cur
    v, r, done = next_value(v_cur, m, step, vmin, k)
    tried = {tv: te for tv, te in (tried or {}).items() if abs(tv - v_cur) > 1e-9}
    e_cur = 1 / m - 1
    if not done and round(v, 6) in tried:
        done = True   # about to revisit a measured value: settle on the better of the two
    if done:
        if tried:
            tv, te = min(tried.items(), key=lambda kv: abs(kv[1]))
            if abs(te) < abs(e_cur) - 0.002:
                return T("{tv:g}로 되돌리고 확정 — 손감각 {v:+.1f}%, 이 칸 단위로는 이게 제일 가까움", tv=tv, v=te*100), True, tv
        return T("{v_cur:g} 확정 — 손감각 {v:+.1f}%, 이 칸 단위로는 이게 제일 가까움", v_cur=v_cur, v=e_cur*100), True, v_cur
    return T("{v:g}로 바꾸고 다시 측정 (예상 오차 {v2:+.1f}%)", v=v, v2=(-r/(1+r))*100), False, v


# =========================================================== PVP play analysis
# While you play, every raw mouse event is logged. Each flick (fast aim move) is
# split into the primary movement and the small corrections after it. If the
# corrections go back the way you came you overshot (sens too high for you); if they
# keep going the same way you undershot (too low). Hip and ADS are separated by
# whether the right mouse button was held when the flick started.
BIN_S = 0.004          # 4 ms bins
V_ON = 6.0             # cm/s, hand is moving
V_FLICK = 25.0         # cm/s peak, counts as a flick
MIN_FLICK_CM = 0.8
MAX_PRIMARY_S = 0.40   # longer = tracking/spraying, skipped
CORR_WINDOW_S = 0.45
SETTLE_S = 0.15
OVER_TH = 0.04         # correction >4% of the flick length
SHARE_LO, SHARE_HI = 0.30, 0.55   # healthy overshoot share
SHOT_AFTER_S = 0.30
MIN_FLICKS = 40    # a left click within this after settling = a flick at an enemy


def bin_events(events, dpi):
    """events: [(t, dx, dy, rmb_held, lmb_down)] -> binned arrays (cm)."""
    if not events or dpi <= 0:
        return None
    ev = np.array(events, dtype=np.float64)
    t0 = ev[0, 0]
    idx = ((ev[:, 0] - t0) / BIN_S).astype(np.int64)
    n = int(idx[-1]) + 1
    k = 2.54 / dpi
    dx = np.bincount(idx, ev[:, 1], n) * k
    dy = np.bincount(idx, ev[:, 2], n) * k
    rmb = np.zeros(n, bool)
    # rmb state: last known per bin
    last = np.full(n, -1.0)
    last[idx] = ev[:, 3]
    cur = 0.0
    for i in range(n):
        if last[i] >= 0:
            cur = last[i]
        rmb[i] = cur > 0.5
    click = np.bincount(idx, ev[:, 4], n) > 0
    return dx, dy, rmb, click


def find_flicks(events, dpi):
    """Returns a list of flick dicts: kind, dist_cm, ratio (signed correction/primary),
    cls ('over'|'under'|'clean'), settle_s."""
    b = bin_events(events, dpi)
    if b is None:
        return []
    dx, dy, rmb, click = b
    n = len(dx)
    sp = np.hypot(dx, dy) / BIN_S
    ker = np.ones(5) / 5
    sp = np.convolve(sp, ker, "same")
    out = []
    i = 0
    settle_bins = int(SETTLE_S / BIN_S)
    while i < n:
        if sp[i] < V_ON:
            i += 1
            continue
        start = i
        # primary: rise to a peak, end at first dip below 35% of peak (or V_ON)
        peak = sp[i]
        j = i
        while j + 1 < n and sp[j + 1] >= sp[j] * 0.98 and (j - start) * BIN_S < MAX_PRIMARY_S:
            j += 1
            peak = max(peak, sp[j])
        # primary ends when the hand stops, or at a speed valley (a new sub-movement begins)
        while j < n and sp[j] > V_ON and (j - start) * BIN_S < MAX_PRIMARY_S:
            if (j + 1 < n and sp[j] < 0.35 * peak and sp[j + 1] > sp[j] * 1.02):
                break
            j += 1
        end = j
        if (end - start) * BIN_S >= MAX_PRIMARY_S:  # tracking / spray: skip until it stops
            while j < n and sp[j] >= V_ON:
                j += 1
            i = j
            continue
        P = np.array([dx[start:end].sum(), dy[start:end].sum()])
        dist = float(np.hypot(*P))
        if peak < V_FLICK or dist < MIN_FLICK_CM:
            i = end + 1
            continue
        # corrections until the hand settles, the window ends, or the next flick
        u = P / dist
        k = end
        quiet = 0
        lim = min(n, end + int(CORR_WINDOW_S / BIN_S))
        while k < lim:
            if sp[k] < V_ON:
                quiet += 1
                if quiet >= settle_bins:
                    break
            else:
                quiet = 0
                if sp[k] >= V_FLICK and k > end + 2 and sp[k] > sp[k - 1] and sp[k - 1] < V_ON:
                    break  # a new flick started
            k += 1
        C = np.array([dx[end:k].sum(), dy[end:k].sum()])
        ratio = float(C @ u) / dist
        cls = "over" if ratio < -OVER_TH else ("under" if ratio > OVER_TH else "clean")
        settle = (k - quiet - start) * BIN_S
        shot = bool(click[start:min(n, k + int(SHOT_AFTER_S / BIN_S))].any())
        out.append({"kind": "ads" if rmb[start] else "hip", "dist": dist, "ratio": ratio, "shot": shot,
                    "cls": cls, "settle": settle, "t": start * BIN_S})
        i = max(k, end + 1)
    return out


def summarize(flicks):
    """Prefer flicks that ended in a shot (aimed at someone). Looking around / checking
    corners has no target, so its corrections say nothing about sensitivity. Falls back
    to all flicks when there are too few shots."""
    res = {}
    for kind in ("hip", "ads"):
        allf = [x for x in flicks if x["kind"] == kind]
        shots = [x for x in allf if x.get("shot")]
        f = shots if len(shots) >= MIN_FLICKS else allf
        o = sum(x["cls"] == "over" for x in f)
        u = sum(x["cls"] == "under" for x in f)
        c = sum(x["cls"] == "clean" for x in f)
        share = o / (o + u) if o + u else None
        res[kind] = {"n": len(f), "shots_only": f is shots and bool(shots), "all": len(allf), "over": o, "under": u, "clean": c, "share": share,
                     "med_ratio": statistics.median([x["ratio"] for x in f]) if f else 0.0,
                     "settle_ms": statistics.median([x["settle"] for x in f]) * 1000 if f else None}
    return res



def tune_factor(st):
    """Session stats -> sens multiplier. 1.0 when overshoot share is healthy.
    Otherwise the median correction tells how far off the sens is: primary moves land
    at about sens/ideal of the target, so ideal ~ sens * (1 + median correction ratio)."""
    share = st.get("share")
    if share is None or SHARE_LO <= share <= SHARE_HI:
        return 1.0
    f = 1 + st.get("med_ratio", 0.0)
    if abs(f - 1) < MATCH_TOL and abs(share - (SHARE_LO + SHARE_HI) / 2) < 0.25:
        return 1.0  # off-balance by chance, but the typical correction is tiny
    if (share > SHARE_HI and f >= 1) or (share < SHARE_LO and f <= 1):  # disagree -> nudge
        f = 0.96 if share > SHARE_HI else 1.04
    return float(min(1.4, max(0.7, f)))


def tune_suggest(history, kind, step, vmin=0.0, pre=1.0):
    """history: sessions [{'values': {'hip': v, 'ads': v}, 'stats': summarize(...)}], newest last.
    pre: feel change already caused by another setting (조준 감도가 일반 감도에 곱해지는
    게임에서 일반 감도를 바꾼 비율). Returns (value, text, final). Brackets: if the last two sessions pointed in opposite
    directions, the answer lies between them -> geometric mean."""
    s = history[-1]
    v = s["values"][kind]
    st = s["stats"][kind]
    name = T("일반") if kind == "hip" else T("조준")
    if st["n"] < MIN_FLICKS:
        return v, T("{name}: 플릭 {n}개 — {MIN_FLICKS}개 이상 필요. 몇 판 더.", name=name, n=st['n'], MIN_FLICKS=MIN_FLICKS), False
    f = tune_factor(st)
    if f == 1.0 and abs(pre - 1) < 1e-9:
        return v, T("{name} {v:g} 확정 — 오버 {v2:.0f}% (적정 {v3:.0f}~{v4:.0f}%)", name=name, v=v, v2=st['share']*100, v3=SHARE_LO*100, v4=SHARE_HI*100), True
    target = v * f
    prev = [h for h in history[:-1] if h["stats"][kind]["n"] >= MIN_FLICKS
            and abs(h["values"][kind] - v) > 1e-9]
    if prev:
        p = prev[-1]
        fp = tune_factor(p["stats"][kind])
        pv = p["values"][kind]
        # previous said go one way, now we say go back -> optimum is between
        if fp != 1.0 and (fp > 1) != (f > 1) and (pv < v) == (f < 1):
            target = (pv * v) ** 0.5
    target /= pre
    nv = snap(target, step, vmin)
    if f == 1.0:
        return nv, T("{name}: {v:g} → {nv:g} (일반 감도 변경분 보정)", name=name, v=v, nv=nv), False
    if abs(nv - v) < 1e-9:
        nv = snap(v + (step if f > 1 else -step), step, vmin)
        if prev and abs(nv - prev[-1]["values"][kind]) < 1e-9:
            better = min([s, prev[-1]], key=lambda h: abs((h["stats"][kind]["share"] or 0.5) - 0.42))
            bv = better["values"][kind]
            return bv, T("{name} {bv:g} 확정 — 칸 단위로는 이게 제일 균형 잡힘", name=name, bv=bv), True
    d = T("낮추기 (지나침 많음)") if f < 1 else T("올리기 (덜 감 많음)")
    return nv, T("{name}: {v:g} → {nv:g} {d}, 오버 {v2:.0f}%", name=name, v=v, nv=nv, d=d, v2=st['share']*100), False


# ------------------------------------------------------ menu vs aiming filter
LOCK_RADIUS = 40      # px from the game-window centre
FREE_STEP = 8         # px the cursor moved between two frames


def cursor_locked(prev, pos, center, moved_counts, was_locked):
    """While aiming, Roblox pins the cursor to the window centre, so the mouse moves but
    the cursor does not. In a menu/map/inventory the cursor travels. Returns new state."""
    if pos is None or center is None:
        return was_locked
    far = abs(pos[0] - center[0]) > LOCK_RADIUS or abs(pos[1] - center[1]) > LOCK_RADIUS
    if far:
        return False
    if moved_counts < 10:
        return was_locked          # no movement: nothing to judge by
    if prev is not None and abs(pos[0] - prev[0]) + abs(pos[1] - prev[1]) > FREE_STEP:
        return False
    return True


# ------------------------------------------------------------------- hotkeys
# A binding is a string like "F7", "CTRL+F7", "SHIFT+ALT+K", "MB4", "MB5".
MODS = {"ALT": 0x1, "CTRL": 0x2, "SHIFT": 0x4}
_VK = {**{f"F{i}": 0x6F + i for i in range(1, 13)},
       **{chr(c): c for c in range(ord("A"), ord("Z") + 1)},
       **{str(d): 0x30 + d for d in range(10)},
       **{f"NUM{d}": 0x60 + d for d in range(10)},
       "INSERT": 0x2D, "DELETE": 0x2E, "HOME": 0x24, "END": 0x23, "PGUP": 0x21, "PGDN": 0x22,
       "PAUSE": 0x13, "SCROLLLOCK": 0x91, "`": 0xC0}
MOUSE_KEYS = {"MB4": 0x0040, "MB5": 0x0100}   # raw-input button-down flags
DEFAULT_KEYS = {"toggle": "F6", "hip": "F7", "ads": "F8"}


def parse_key(spec):
    """-> ('kbd', mods, vk) | ('mouse', flag) | None"""
    if not spec:
        return None
    parts = spec.upper().split("+")
    key = parts[-1]
    if key in MOUSE_KEYS and len(parts) == 1:
        return ("mouse", MOUSE_KEYS[key])
    mods = 0
    for p in parts[:-1]:
        if p not in MODS:
            return None
        mods |= MODS[p]
    vk = _VK.get(key)
    return ("kbd", mods, vk) if vk else None


_PG_NAMES = {"insert": "INSERT", "delete": "DELETE", "home": "HOME", "end": "END",
             "page up": "PGUP", "page down": "PGDN", "pause": "PAUSE", "scroll lock": "SCROLLLOCK",
             "`": "`"}


def spec_from_pygame(name, ctrl=False, alt=False, shift=False):
    """pygame.key.name() + modifier state -> binding string, or None if unsupported."""
    n = name.lower()
    if n.startswith("[") and n.endswith("]") and n[1:-1].isdigit():
        key = "NUM" + n[1:-1]
    elif n in _PG_NAMES:
        key = _PG_NAMES[n]
    else:
        key = n.upper()
    if key not in _VK:
        return None
    mods = [m for m, on in (("CTRL", ctrl), ("ALT", alt), ("SHIFT", shift)) if on]
    return "+".join(mods + [key])


def check_bindings(b):
    """Problems with a full bindings dict (duplicates / unparsable)."""
    errs = []
    seen = {}
    for act, spec in b.items():
        if parse_key(spec) is None:
            errs.append(T("{act}: '{spec}' 지원 안 하는 키", act=act, spec=spec))
        elif spec.upper() in seen:
            errs.append(T("'{spec}' 중복 ({v}, {act})", spec=spec, v=seen[spec.upper()], act=act))
        else:
            seen[spec.upper()] = act
    return errs


def overlay_pos(corner, screen, size, margin=12):
    """corner: 'tl'|'tr'|'bl'|'br'; screen: (left, top, w, h) -> window top-left."""
    l, t, w, h = screen
    x = l + margin if corner in ("tl", "bl") else l + w - size[0] - margin
    y = t + margin if corner in ("tl", "tr") else t + h - size[1] - margin
    return x, y


def steps_look_identical(steps):
    """2+ measured steps within 8% of each other: the DPI button almost certainly wasn't
    changed (or every swipe stopped at the same on-screen point)."""
    d = [s.dpi for s in steps if s.dpi > 0]
    return len(d) >= 2 and max(d) / min(d) < 1.08


MIN_SWIPE = 300   # counts; anything shorter is a mis-click, not a pad-length swipe
STOP_HOLD_S = 0.5  # still this long after moving = reached the end point


def ratio_plausible(counts, first_counts):
    """Same physical distance at another DPI step: ratio must stay in a sane range."""
    if first_counts <= 0:
        return True
    r = counts / first_counts
    return 0.08 <= r <= 40

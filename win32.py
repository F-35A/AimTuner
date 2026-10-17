"""Windows platform layer: raw mouse input, global hotkeys, SendInput, screen grab,
pointer settings, overlay window styling. All via ctypes (no extra packages).
"""
from __future__ import annotations

import ctypes
import sys
import threading
from ctypes import wintypes as wt

import numpy as np

IS_WIN = sys.platform == "win32"
LRESULT = ctypes.c_ssize_t
ULONG_PTR = ctypes.c_size_t


# ------------------------------------------------------------------ structs
# fixed-width ints so layouts match 64-bit Windows on any host (testable on Linux)
U16, U32, I32 = ctypes.c_uint16, ctypes.c_uint32, ctypes.c_int32


class POINT(ctypes.Structure):
    _fields_ = [("x", I32), ("y", I32)]

class RAWINPUTDEVICE(ctypes.Structure):
    _fields_ = [("usUsagePage", U16), ("usUsage", U16),
                ("dwFlags", U32), ("hwndTarget", wt.HWND)]


class RAWINPUTHEADER(ctypes.Structure):
    _fields_ = [("dwType", U32), ("dwSize", U32),
                ("hDevice", wt.HANDLE), ("wParam", wt.WPARAM)]


class RAWMOUSE(ctypes.Structure):
    _fields_ = [("usFlags", U16), ("ulButtons", U32), ("ulRawButtons", U32),
                ("lLastX", I32), ("lLastY", I32), ("ulExtraInformation", U32)]


class RAWINPUT(ctypes.Structure):
    _fields_ = [("header", RAWINPUTHEADER), ("mouse", RAWMOUSE)]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", I32), ("dy", I32), ("mouseData", U32),
                ("dwFlags", U32), ("time", U32), ("dwExtraInfo", ULONG_PTR)]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", U16), ("wScan", U16), ("dwFlags", U32),
                ("time", U32), ("dwExtraInfo", ULONG_PTR)]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", U32), ("wParamL", U16), ("wParamH", U16)]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", U32), ("u", _INPUTUNION)]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", U32), ("biWidth", I32), ("biHeight", I32),
                ("biPlanes", U16), ("biBitCount", U16), ("biCompression", U32),
                ("biSizeImage", U32), ("biXPelsPerMeter", I32), ("biYPelsPerMeter", I32),
                ("biClrUsed", U32), ("biClrImportant", U32)]


class MSG(ctypes.Structure):
    _fields_ = [("hwnd", wt.HWND), ("message", U32), ("wParam", wt.WPARAM),
                ("lParam", wt.LPARAM), ("time", U32), ("pt", POINT)]


WM_INPUT, WM_HOTKEY, WM_CLOSE, WM_DESTROY = 0x00FF, 0x0312, 0x0010, 0x0002
RIDEV_INPUTSINK = 0x00000100
RID_INPUT = 0x10000003
RIM_TYPEMOUSE = 0
MOUSE_MOVE_ABSOLUTE = 0x01
INPUT_MOUSE, MOUSEEVENTF_MOVE = 0, 0x0001
MOD_NOREPEAT = 0x4000
HWND_MESSAGE = wt.HWND(-3)
SPI_GETMOUSE, SPI_SETMOUSE, SPI_GETMOUSESPEED, SPI_SETMOUSESPEED = 0x03, 0x04, 0x70, 0x71
SPIF = 0x01 | 0x02

INJECT_TAG = 0xA17E7E11  # dwExtraInfo on our SendInput moves; shows up in raw input
WM_REREG = 0x8000 + 1  # WM_APP+1: take raw input back
WM_REKEY = 0x8000 + 2  # WM_APP+2: apply new hotkey bindings


class Win32Platform:
    def __init__(self):
        self.u = ctypes.WinDLL("user32", use_last_error=True)
        self.g = ctypes.WinDLL("gdi32", use_last_error=True)
        self.k = ctypes.WinDLL("kernel32", use_last_error=True)
        u, g = self.u, self.g
        self.WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM)
        u.DefWindowProcW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
        u.DefWindowProcW.restype = LRESULT
        u.CreateWindowExW.argtypes = [wt.DWORD, wt.LPCWSTR, wt.LPCWSTR, wt.DWORD, ctypes.c_int, ctypes.c_int,
                                      ctypes.c_int, ctypes.c_int, wt.HWND, wt.HMENU, wt.HINSTANCE, wt.LPVOID]
        u.CreateWindowExW.restype = wt.HWND
        u.GetRawInputData.argtypes = [wt.HANDLE, wt.UINT, wt.LPVOID, ctypes.POINTER(wt.UINT), wt.UINT]
        u.GetRawInputData.restype = wt.UINT
        u.GetRawInputBuffer.argtypes = [wt.LPVOID, ctypes.POINTER(wt.UINT), wt.UINT]
        u.GetRawInputBuffer.restype = wt.UINT
        u.RegisterRawInputDevices.argtypes = [ctypes.POINTER(RAWINPUTDEVICE), wt.UINT, wt.UINT]
        u.SendInput.argtypes = [wt.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
        u.SendInput.restype = wt.UINT
        u.GetForegroundWindow.restype = wt.HWND
        u.RegisterHotKey.argtypes = [wt.HWND, ctypes.c_int, wt.UINT, wt.UINT]
        u.UnregisterHotKey.argtypes = [wt.HWND, ctypes.c_int]
        u.DestroyWindow.argtypes = [wt.HWND]
        u.GetMessageW.argtypes = [ctypes.POINTER(MSG), wt.HWND, wt.UINT, wt.UINT]
        u.TranslateMessage.argtypes = [ctypes.POINTER(MSG)]
        u.DispatchMessageW.argtypes = [ctypes.POINTER(MSG)]
        u.DispatchMessageW.restype = LRESULT
        u.SystemParametersInfoW.argtypes = [wt.UINT, wt.UINT, ctypes.c_void_p, wt.UINT]
        u.RegisterClassExW.argtypes = [ctypes.c_void_p]
        u.RegisterClassExW.restype = wt.ATOM
        u.GetClientRect.argtypes = [wt.HWND, ctypes.POINTER(wt.RECT)]
        u.ClientToScreen.argtypes = [wt.HWND, ctypes.POINTER(wt.POINT)]
        u.GetDC.argtypes = [wt.HWND]
        u.GetDC.restype = wt.HDC
        u.ReleaseDC.argtypes = [wt.HWND, wt.HDC]
        u.PostMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
        u.SetWindowLongPtrW.argtypes = [wt.HWND, ctypes.c_int, ctypes.c_ssize_t]
        u.SetWindowLongPtrW.restype = ctypes.c_ssize_t
        u.GetWindowLongPtrW.argtypes = [wt.HWND, ctypes.c_int]
        u.GetWindowLongPtrW.restype = ctypes.c_ssize_t
        u.SetWindowPos.argtypes = [wt.HWND, wt.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wt.UINT]
        u.SetLayeredWindowAttributes.argtypes = [wt.HWND, wt.COLORREF, wt.BYTE, wt.DWORD]
        u.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
        g.CreateCompatibleDC.argtypes = [wt.HDC]
        g.CreateCompatibleDC.restype = wt.HDC
        g.CreateCompatibleBitmap.argtypes = [wt.HDC, ctypes.c_int, ctypes.c_int]
        g.CreateCompatibleBitmap.restype = wt.HBITMAP
        g.SelectObject.argtypes = [wt.HDC, wt.HGDIOBJ]
        g.SelectObject.restype = wt.HGDIOBJ
        g.BitBlt.argtypes = [wt.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                             wt.HDC, ctypes.c_int, ctypes.c_int, wt.DWORD]
        g.GetDIBits.argtypes = [wt.HDC, wt.HBITMAP, wt.UINT, wt.UINT, wt.LPVOID, ctypes.c_void_p, wt.UINT]
        g.DeleteObject.argtypes = [wt.HGDIOBJ]
        g.DeleteDC.argtypes = [wt.HDC]
        k = self.k
        k.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
        k.OpenProcess.restype = wt.HANDLE
        k.QueryFullProcessImageNameW.argtypes = [wt.HANDLE, wt.DWORD, wt.LPWSTR, ctypes.POINTER(wt.DWORD)]
        k.CloseHandle.argtypes = [wt.HANDLE]
        k.GetModuleHandleW.argtypes = [wt.LPCWSTR]
        k.GetModuleHandleW.restype = wt.HMODULE
        self.hwnd = None
        self.thread = None
        self._hdr = ctypes.sizeof(RAWINPUTHEADER)
        self._one = ctypes.create_string_buffer(256)
        self._buf = ctypes.create_string_buffer(64 * 1024)
        self.own_hwnd = None   # app window, never treated as the game
        self._ready = threading.Event()
        self.hotkey_ok = {}
        self.keys = {}            # id -> (mods, vk)
        self._registered = set()

    # ------------------------------------------------ raw input + hotkeys thread
    def start(self, on_raw, on_hotkey):
        self.on_raw, self.on_hotkey = on_raw, on_hotkey
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        self._ready.wait(3)

    def _wndproc(self, hwnd, msg, wp, lp):
        if msg == WM_INPUT:
            # Read this message's data, then drain everything else already queued in one go.
            # One-event-per-message is too slow from Python under load (events get dropped).
            size = wt.UINT(ctypes.sizeof(self._one))
            if self.u.GetRawInputData(lp, RID_INPUT, self._one, ctypes.byref(size), self._hdr) != 0xFFFFFFFF:
                self._emit(RAWINPUT.from_buffer_copy(self._one))
            self._drain()
            return self.u.DefWindowProcW(hwnd, msg, wp, lp)
        if msg == WM_REREG:
            self._register_raw()
            return 0
        if msg == WM_REKEY:
            self._apply_keys()
            return 0
        if msg == WM_HOTKEY:
            try:
                self.on_hotkey(int(wp))
            except Exception:
                pass
            return 0
        if msg == WM_CLOSE:
            self.u.DestroyWindow(hwnd)
            return 0
        if msg == WM_DESTROY:
            self.u.PostQuitMessage(0)
            return 0
        return self.u.DefWindowProcW(hwnd, msg, wp, lp)

    def _emit(self, ri):
        if ri.header.dwType != RIM_TYPEMOUSE or (ri.mouse.usFlags & MOUSE_MOVE_ABSOLUTE):
            return
        dev = ri.header.hDevice or 0
        if ri.mouse.ulExtraInformation == INJECT_TAG:
            dev = 0  # our own probe movement, not the user's hand
        try:
            self.on_raw(ri.mouse.lLastX, ri.mouse.lLastY, ri.mouse.ulButtons & 0xFFFF, dev)
        except Exception:
            pass

    def _drain(self):
        """GetRawInputBuffer: pull every pending raw input block (8-byte aligned on x64)."""
        for _ in range(64):
            size = wt.UINT(len(self._buf))
            n = self.u.GetRawInputBuffer(self._buf, ctypes.byref(size), self._hdr)
            if n == 0 or n == 0xFFFFFFFF:
                return
            for ri in parse_blocks(self._buf.raw, n):
                self._emit(ri)

    def _loop(self):
        u = self.u
        hinst = self.k.GetModuleHandleW(None)

        class WNDCLASSEXW(ctypes.Structure):
            _fields_ = [("cbSize", wt.UINT), ("style", wt.UINT), ("lpfnWndProc", self.WNDPROC),
                        ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int), ("hInstance", wt.HINSTANCE),
                        ("hIcon", wt.HICON), ("hCursor", wt.HANDLE), ("hbrBackground", wt.HBRUSH),
                        ("lpszMenuName", wt.LPCWSTR), ("lpszClassName", wt.LPCWSTR), ("hIconSm", wt.HICON)]
        self._proc = self.WNDPROC(self._wndproc)  # keep a reference
        wc = WNDCLASSEXW()
        wc.cbSize = ctypes.sizeof(WNDCLASSEXW)
        wc.lpfnWndProc = self._proc
        wc.hInstance = hinst
        wc.lpszClassName = "AimTunerRawSink"
        u.RegisterClassExW(ctypes.byref(wc))
        self.hwnd = u.CreateWindowExW(0, "AimTunerRawSink", "AimTuner", 0, 0, 0, 0, 0,
                                      HWND_MESSAGE, None, hinst, None)
        self._register_raw()
        self._apply_keys()
        self._ready.set()
        msg = MSG()
        while u.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            u.TranslateMessage(ctypes.byref(msg))
            u.DispatchMessageW(ctypes.byref(msg))
        for hid in list(self._registered):
            u.UnregisterHotKey(self.hwnd, hid)

    def _apply_keys(self):
        u = self.u
        for hid in list(self._registered):
            u.UnregisterHotKey(self.hwnd, hid)
        self._registered.clear()
        self.hotkey_ok = {}
        for hid, (mods, vk) in self.keys.items():
            ok = bool(u.RegisterHotKey(self.hwnd, hid, MOD_NOREPEAT | mods, vk))
            self.hotkey_ok[hid] = ok
            if ok:
                self._registered.add(hid)

    def set_hotkeys(self, keys):
        """keys: {id: (mods, vk)} keyboard hotkeys (mouse buttons are handled by the app)."""
        self.keys = dict(keys)
        if self.hwnd:
            self.u.PostMessageW(self.hwnd, WM_REKEY, 0, 0)

    def _register_raw(self):
        rid = RAWINPUTDEVICE(0x01, 0x02, RIDEV_INPUTSINK, self.hwnd)
        self.raw_ok = bool(self.u.RegisterRawInputDevices(ctypes.byref(rid), 1, ctypes.sizeof(RAWINPUTDEVICE)))

    def reregister(self):
        """SDL/pygame can steal the process-wide raw-mouse registration; take it back."""
        if self.hwnd:
            self.u.PostMessageW(self.hwnd, WM_REREG, 0, 0)

    def stop(self):
        if self.hwnd:
            self.u.PostMessageW(self.hwnd, WM_CLOSE, 0, 0)

    # ---------------------------------------------------------------- inject
    def inject(self, dx, dy):
        """Relative mouse move as if from a mouse. Split into chunks of <=60 counts."""
        n = max(1, int(max(abs(dx), abs(dy)) // 60) + 1)
        arr = (INPUT * n)()
        sx = sy = 0
        for i in range(n):
            tx = round(dx * (i + 1) / n)
            ty = round(dy * (i + 1) / n)
            arr[i].type = INPUT_MOUSE
            arr[i].u.mi = MOUSEINPUT(tx - sx, ty - sy, 0, MOUSEEVENTF_MOVE, 0, INJECT_TAG)
            sx, sy = tx, ty
        self.u.SendInput(n, arr, ctypes.sizeof(INPUT))

    # ------------------------------------------------------------ game window
    def game_rect(self):
        h = self.u.GetForegroundWindow()
        if not h or h == self.own_hwnd:
            return None
        rc = wt.RECT()
        self.u.GetClientRect(h, ctypes.byref(rc))
        pt = wt.POINT(0, 0)
        self.u.ClientToScreen(h, ctypes.byref(pt))
        return (pt.x, pt.y, rc.right - rc.left, rc.bottom - rc.top)

    def cursor_pos(self):
        pt = POINT()
        if self.u.GetCursorPos(ctypes.byref(pt)):
            return (pt.x, pt.y)
        return None

    def fg_process(self):
        """Executable name of the foreground window (e.g. RobloxPlayerBeta.exe)."""
        h = self.u.GetForegroundWindow()
        if not h:
            return ""
        pid = wt.DWORD()
        self.u.GetWindowThreadProcessId(h, ctypes.byref(pid))
        hp = self.k.OpenProcess(0x1000, False, pid.value)  # QUERY_LIMITED_INFORMATION
        if not hp:
            return ""
        try:
            buf = ctypes.create_unicode_buffer(520)
            n = wt.DWORD(520)
            if self.k.QueryFullProcessImageNameW(hp, 0, buf, ctypes.byref(n)):
                return buf.value.split("\\")[-1]
            return ""
        finally:
            self.k.CloseHandle(hp)

    def grab(self, reg):
        l, t, w, h = reg
        u, g = self.u, self.g
        sdc = u.GetDC(None)
        mdc = g.CreateCompatibleDC(sdc)
        bmp = g.CreateCompatibleBitmap(sdc, w, h)
        old = g.SelectObject(mdc, bmp)
        g.BitBlt(mdc, 0, 0, w, h, sdc, l, t, 0x00CC0020 | 0x40000000)  # SRCCOPY | CAPTUREBLT
        bi = BITMAPINFOHEADER(ctypes.sizeof(BITMAPINFOHEADER), w, -h, 1, 32, 0, 0, 0, 0, 0, 0)
        buf = np.empty((h, w, 4), np.uint8)
        g.GetDIBits(mdc, bmp, 0, h, buf.ctypes.data, ctypes.byref(bi), 0)
        g.SelectObject(mdc, old)
        g.DeleteObject(bmp)
        g.DeleteDC(mdc)
        u.ReleaseDC(None, sdc)
        return (buf[..., 2] * 0.299 + buf[..., 1] * 0.587 + buf[..., 0] * 0.114).astype(np.float32)

    # ---------------------------------------------------------- windows mouse
    def win_get(self):
        sp = ctypes.c_int()
        self.u.SystemParametersInfoW(SPI_GETMOUSESPEED, 0, ctypes.byref(sp), 0)
        arr = (ctypes.c_int * 3)()
        self.u.SystemParametersInfoW(SPI_GETMOUSE, 0, arr, 0)
        return sp.value, bool(arr[2])

    def _set_raw(self, speed, mouse3):
        self.u.SystemParametersInfoW(SPI_SETMOUSESPEED, 0, ctypes.c_void_p(int(speed)), SPIF)
        arr = (ctypes.c_int * 3)(*mouse3)
        self.u.SystemParametersInfoW(SPI_SETMOUSE, 0, arr, SPIF)

    def win_set(self, speed, epp):
        """Set pointer speed + Enhance Pointer Precision, then read back. If Windows did not
        take exactly these values, put the old ones back and report failure."""
        speed = max(1, min(20, int(speed)))
        old_speed = ctypes.c_int()
        self.u.SystemParametersInfoW(SPI_GETMOUSESPEED, 0, ctypes.byref(old_speed), 0)
        old = (ctypes.c_int * 3)()
        self.u.SystemParametersInfoW(SPI_GETMOUSE, 0, old, 0)
        self._set_raw(speed, [6, 10, 1] if epp else [0, 0, 0])
        if self.win_get() == (speed, bool(epp)):
            return True
        if 1 <= old_speed.value <= 20:
            self._set_raw(old_speed.value, list(old))
        return False

    # --------------------------------------------------------------- overlay
    def screen_rect(self):
        r = self.game_rect()
        if r:
            return r
        return (0, 0, self.u.GetSystemMetrics(0), self.u.GetSystemMetrics(1))

    def overlay(self, on, hwnd, size=None, pos=(12, 12), alpha=225):
        """Turn the app window into a small always-on-top click-through HUD (or back)."""
        GWL_STYLE, GWL_EXSTYLE = -16, -20
        WS_POPUP, WS_OVERLAPPEDWINDOW = 0x80000000, 0x00CF0000
        WS_EX_LAYERED, WS_EX_TRANSPARENT, WS_EX_TOPMOST, WS_EX_TOOLWINDOW, WS_EX_NOACTIVATE = \
            0x80000, 0x20, 0x8, 0x80, 0x08000000
        HWND_TOPMOST, HWND_NOTOPMOST = wt.HWND(-1), wt.HWND(-2)
        SWP_FRAMECHANGED, SWP_SHOWWINDOW, SWP_NOMOVE, SWP_NOSIZE = 0x20, 0x40, 0x2, 0x1
        u = self.u
        if on:
            if getattr(self, "_saved", None) is None:
                self._saved = (u.GetWindowLongPtrW(hwnd, GWL_STYLE), u.GetWindowLongPtrW(hwnd, GWL_EXSTYLE))
            u.SetWindowLongPtrW(hwnd, GWL_STYLE, (self._saved[0] & ~WS_OVERLAPPEDWINDOW) | WS_POPUP)
            u.SetWindowLongPtrW(hwnd, GWL_EXSTYLE, self._saved[1] | WS_EX_LAYERED | WS_EX_TRANSPARENT
                                | WS_EX_TOPMOST | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE)
            u.SetLayeredWindowAttributes(hwnd, 0, int(alpha), 0x2)
            w, h = size
            u.SetWindowPos(hwnd, HWND_TOPMOST, int(pos[0]), int(pos[1]), w, h, SWP_FRAMECHANGED | SWP_SHOWWINDOW)
        elif getattr(self, "_saved", None):
            u.SetWindowLongPtrW(hwnd, GWL_STYLE, self._saved[0])
            u.SetWindowLongPtrW(hwnd, GWL_EXSTYLE, self._saved[1])
            u.SetWindowPos(hwnd, HWND_NOTOPMOST, 80, 60, size[0], size[1], SWP_FRAMECHANGED | SWP_SHOWWINDOW)
            self._saved = None

    def beep(self, ok=True):
        try:
            import winsound
            winsound.Beep(1200 if ok else 400, 90 if ok else 250)
        except Exception:
            pass


def parse_blocks(data, n):
    """RAWINPUT blocks from a GetRawInputBuffer result (x64: each block 8-byte aligned)."""
    out, off = [], 0
    hsz, rsz = ctypes.sizeof(RAWINPUTHEADER), ctypes.sizeof(RAWINPUT)
    for _ in range(n):
        if off + hsz > len(data):
            break
        hdr = RAWINPUTHEADER.from_buffer_copy(data[off:off + hsz])
        if hdr.dwSize < hsz or off + hdr.dwSize > len(data):
            break
        if hdr.dwType == RIM_TYPEMOUSE and off + rsz <= len(data):
            out.append(RAWINPUT.from_buffer_copy(data[off:off + rsz]))
        off = (off + hdr.dwSize + 7) & ~7
    return out


def struct_sizes():
    """For tests: 64-bit Windows sizes of the structs we hand to the OS."""
    return {"INPUT": ctypes.sizeof(INPUT), "RAWINPUTHEADER": ctypes.sizeof(RAWINPUTHEADER),
            "RAWMOUSE": ctypes.sizeof(RAWMOUSE), "MSG": ctypes.sizeof(MSG),
            "BITMAPINFOHEADER": ctypes.sizeof(BITMAPINFOHEADER)}

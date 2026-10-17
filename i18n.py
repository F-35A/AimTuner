"""Tiny i18n: T("한국어 원문 {x}", x=...) -> English when LANG == "en".

The Korean source text is the key, English lives in lang_en.py. The language is
chosen once at start-up (saved setting > AIMTUNER_LANG env > Windows UI language),
so switching it takes effect after a restart.
"""
from __future__ import annotations

import json
import os
import sys

LANGS = ("ko", "en")


def _state_file():
    return os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "AimTuner", "state.json")


def detect():
    env = os.environ.get("AIMTUNER_LANG")
    if env in LANGS:
        return env
    try:
        with open(_state_file(), encoding="utf-8") as f:
            lang = json.load(f).get("ui", {}).get("lang")
            if lang in LANGS:
                return lang
    except Exception:
        pass
    if sys.platform == "win32":
        try:
            import ctypes
            return "ko" if ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF == 0x12 else "en"
        except Exception:
            return "en"
    return "ko" if os.environ.get("LANG", "").startswith("ko") else "en"


LANG = detect()


def T(text, **kw):
    if LANG == "en":
        from lang_en import EN
        text = EN.get(text, text)
    return text.format(**kw) if kw else text

"""Is the person crouching right now? Where the game does not say (every game but H2A and Halo 4, tools/botctl.py
owner_crouch), the bots would aim at a crouched man's standing head height, so tools/live_bots.py asks whether the key
bound to crouch in MCC's own settings is held. Only that one key, only while MCC is the window in front, and only as
"held now": nothing is saved or sent anywhere.
"""
import ctypes
import os
import re

SETTINGS = os.path.join(os.environ.get("LOCALAPPDATA", ""), "..", "LocalLow", "MCC", "Saved", "Config",
                        "WindowsNoEditor", "GameUserSettings.ini")
CROUCH = 9                 # MCC's AbstractButton number for crouch in CustomKeyboardMouseMappingV2
LCTRL = 162                # MCC's default crouch key


def crouch_keys(text):
    """The virtual keys bound to crouch in any game's set of MCC's settings text."""
    out = set()
    for ab, vks in re.findall(r"AbstractButton=(\d+),((?:VirtualKeyCodes\[\d\]=\d+,?)+)", text):
        if int(ab) == CROUCH:
            out |= {int(v) for v in re.findall(r"=(\d+)", vks) if int(v)}
    return sorted(out)


def in_front(pid):
    """Whether process pid owns the window in front."""
    user32 = ctypes.windll.user32
    p = ctypes.c_ulong(0)
    user32.GetWindowThreadProcessId(user32.GetForegroundWindow(), ctypes.byref(p))
    return p.value == pid


def crouch_held(pid, state=None, front=None, vks=None):
    """-> () -> True while a crouch key is held with MCC (process pid) the window in front. MCC's crouch is held.
    ponytail: keyboard only; a controller's crouch needs its binding read."""
    if vks is None:
        try:
            vks = crouch_keys(open(SETTINGS, encoding="utf-8", errors="replace").read())
        except OSError:
            vks = []
    vks = vks or [LCTRL]
    if state is None:
        user32 = ctypes.windll.user32
        state = lambda vk: bool(user32.GetAsyncKeyState(vk) & 0x8000)   # noqa: E731
    front = front or (lambda: in_front(pid))
    return lambda: front() and any(state(vk) for vk in vks)


if __name__ == "__main__":
    line = ("GameKeyboardMouseMappings[1]=(AbstractButton=9,VirtualKeyCodes[0]=67,VirtualKeyCodes[1]=162),"
            "GameKeyboardMouseMappings[2]=(AbstractButton=0,VirtualKeyCodes[0]=32,VirtualKeyCodes[1]=0)")
    assert crouch_keys(line) == [67, 162], crouch_keys(line)
    held = {67}
    assert crouch_held(1, state=lambda vk: vk in held, front=lambda: True, vks=[67])()
    assert not crouch_held(1, state=lambda vk: vk in held, front=lambda: False, vks=[67])()
    assert not crouch_held(1, state=lambda vk: False, front=lambda: True, vks=[67])()
    print("crouch key OK")

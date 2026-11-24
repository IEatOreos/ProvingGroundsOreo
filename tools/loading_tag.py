"""The loading banner on screen from the moment Play starts MCC until botcore's overlay is up (tools/launch.py).

MCC reaches its menus before the mod is loaded (the mod is loaded about 15 s after MCC starts): the banner shows the
bots are still loading. It is a topmost, click-through window with no border (it takes no focus and no clicks) in the
top middle of MCC's window, made with plain Win32 calls. It closes when botcore's overlay has drawn its first frame (it
creates the event LOCAL\\PPG_overlay_ready then: native/overlay.cpp), or after `timeout` seconds.
It is drawn by tools/loading_banner.py (see-through panel, the Project Noble badge, a sliding bar, a light streak) on a
per-pixel-alpha window (UpdateLayeredWindow), fading in and out; if that cannot run, the plain one-line tag shows instead.

(upstream 0.3.0, build 20261119-1940) his, for the banner. (custom, Nov 24) Project Noble's name; the plain tag's text
is no longer his loading message (#60, skipped by the owner): it says only that the bots are loading.

    tag = LoadingTag(); tag.start()  ...  tag.wait_ready(timeout=120)   (closes the window)
"""
import ctypes
import ctypes.wintypes as W
import threading
import time

READY_EVENT = "Local\\PPG_overlay_ready"
TEXT = "Project Noble is loading the bots ..."     # (custom, Nov 24) the plain tag, if the banner cannot draw
WS_POPUP, WS_EX_TOPMOST, WS_EX_TOOLWINDOW, WS_EX_NOACTIVATE, WS_EX_LAYERED, WS_EX_TRANSPARENT = (
    0x80000000, 0x8, 0x80, 0x08000000, 0x80000, 0x20)
WM_PAINT, WM_DESTROY, WM_CLOSE = 0x000F, 0x0002, 0x0010
LRESULT = ctypes.c_ssize_t


class WNDCLASS(ctypes.Structure):
    _fields_ = [("style", W.UINT), ("lpfnWndProc", ctypes.c_void_p), ("cbClsExtra", ctypes.c_int),
                ("cbWndExtra", ctypes.c_int), ("hInstance", W.HINSTANCE), ("hIcon", W.HICON), ("hCursor", W.HANDLE),
                ("hbrBackground", W.HBRUSH), ("lpszMenuName", W.LPCWSTR), ("lpszClassName", W.LPCWSTR)]


class PAINTSTRUCT(ctypes.Structure):
    _fields_ = [("hdc", W.HDC), ("fErase", W.BOOL), ("rcPaint", W.RECT), ("fRestore", W.BOOL), ("fIncUpdate", W.BOOL),
                ("rgbReserved", ctypes.c_byte * 32)]


def _api():
    u, g, k = ctypes.windll.user32, ctypes.windll.gdi32, ctypes.windll.kernel32
    WNDPROC = ctypes.WINFUNCTYPE(LRESULT, W.HWND, W.UINT, W.WPARAM, W.LPARAM)
    u.DefWindowProcW.argtypes = [W.HWND, W.UINT, W.WPARAM, W.LPARAM]
    u.DefWindowProcW.restype = LRESULT
    u.CreateWindowExW.argtypes = [W.DWORD, W.LPCWSTR, W.LPCWSTR, W.DWORD, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                  ctypes.c_int, W.HWND, W.HMENU, W.HINSTANCE, W.LPVOID]
    u.CreateWindowExW.restype = W.HWND
    u.BeginPaint.argtypes = [W.HWND, ctypes.POINTER(PAINTSTRUCT)]
    u.BeginPaint.restype = W.HDC
    u.EndPaint.argtypes = [W.HWND, ctypes.POINTER(PAINTSTRUCT)]
    u.FillRect.argtypes = [W.HDC, ctypes.POINTER(W.RECT), W.HBRUSH]
    u.DrawTextW.argtypes = [W.HDC, W.LPCWSTR, ctypes.c_int, ctypes.POINTER(W.RECT), W.UINT]
    u.GetClientRect.argtypes = [W.HWND, ctypes.POINTER(W.RECT)]
    g.CreateSolidBrush.restype = W.HBRUSH
    g.DeleteObject.argtypes = [W.HANDLE]
    g.SetBkMode.argtypes = [W.HDC, ctypes.c_int]
    g.SetTextColor.argtypes = [W.HDC, W.DWORD]
    u.SetWindowPos.argtypes = [W.HWND, W.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, W.UINT]
    g.CreateFontW.restype = W.HANDLE
    g.SelectObject.argtypes = [W.HDC, W.HANDLE]
    k.OpenEventW.restype = W.HANDLE
    return u, g, k, WNDPROC


def mcc_rect():
    """(left, top, right, bottom) of MCC's window, else the primary screen."""
    u = ctypes.windll.user32
    found = []

    @ctypes.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)
    def each(h, _):
        if u.IsWindowVisible(h):
            b = ctypes.create_unicode_buffer(256)
            u.GetWindowTextW(h, b, 256)
            if b.value.startswith("Halo: The Master Chief Collection"):
                r = W.RECT()
                u.GetWindowRect(h, ctypes.byref(r))
                if r.right - r.left > 400:
                    found.append((r.left, r.top, r.right, r.bottom))
        return True
    u.EnumWindows(each, 0)
    return found[0] if found else (0, 0, u.GetSystemMetrics(0), u.GetSystemMetrics(1))


class LoadingTag:
    def __init__(self, text=TEXT):
        self.text = text
        self.hwnd = None
        self._stop = threading.Event()
        self._thread = None

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def ready(self):
        """True once botcore's overlay has drawn a frame."""
        h = ctypes.windll.kernel32.OpenEventW(0x100000, False, READY_EVENT)       # SYNCHRONIZE
        if h:
            ctypes.windll.kernel32.CloseHandle(h)
        return bool(h)

    def wait_ready(self, timeout=120):
        """Waits for the overlay (or timeout seconds), then closes the tag. True when the overlay came up."""
        end = time.time() + timeout
        while time.time() < end and not self.ready():
            time.sleep(0.5)
        ok = self.ready()
        self.close()
        return ok

    def close(self):
        self._stop.set()
        if self._thread:
            self._thread.join(3)

    def _run(self):
        try:
            self._run_banner()
        except Exception:
            if not self._stop.is_set():
                self._run_plain()                                               # (the plain tag: GDI text, always works)

    def _run_banner(self):
        """The banner: a frame about 30 times a second through UpdateLayeredWindow, following MCC's window."""
        import os
        import sys
        here = os.path.dirname(os.path.abspath(__file__))
        if here not in sys.path:                                                 # (python -I leaves the script's folder out)
            sys.path.insert(0, here)
        import loading_banner
        u, g, k, WNDPROC = _api()
        try:
            u.SetProcessDPIAware()
        except Exception:
            pass

        class BITMAPINFOHEADER(ctypes.Structure):
            _fields_ = [("biSize", W.DWORD), ("biWidth", W.LONG), ("biHeight", W.LONG), ("biPlanes", W.WORD),
                        ("biBitCount", W.WORD), ("biCompression", W.DWORD), ("biSizeImage", W.DWORD),
                        ("biXPelsPerMeter", W.LONG), ("biYPelsPerMeter", W.LONG), ("biClrUsed", W.DWORD),
                        ("biClrImportant", W.DWORD)]

        class BLENDFUNCTION(ctypes.Structure):
            _fields_ = [("BlendOp", ctypes.c_ubyte), ("BlendFlags", ctypes.c_ubyte),
                        ("SourceConstantAlpha", ctypes.c_ubyte), ("AlphaFormat", ctypes.c_ubyte)]

        g.CreateCompatibleDC.restype = W.HDC                                    # (every handle typed: a 64-bit handle
        g.CreateCompatibleDC.argtypes = [W.HDC]                                 #  passed as an int overflowed, at random)
        g.DeleteDC.argtypes = [W.HDC]
        u.ReleaseDC.argtypes = [W.HWND, W.HDC]
        u.GetDC.argtypes = [W.HWND]
        u.DestroyWindow.argtypes = [W.HWND]
        u.ShowWindow.argtypes = [W.HWND, ctypes.c_int]
        u.RegisterClassW.argtypes = [ctypes.c_void_p]
        k.GetModuleHandleW.restype = W.HMODULE
        k.GetModuleHandleW.argtypes = [W.LPCWSTR]
        g.CreateDIBSection.restype = W.HANDLE
        g.CreateDIBSection.argtypes = [W.HDC, ctypes.c_void_p, W.UINT, ctypes.POINTER(ctypes.c_void_p), W.HANDLE, W.DWORD]
        u.UpdateLayeredWindow.argtypes = [W.HWND, W.HDC, ctypes.POINTER(W.POINT), ctypes.POINTER(W.SIZE), W.HDC,
                                          ctypes.POINTER(W.POINT), W.DWORD, ctypes.POINTER(BLENDFUNCTION), W.DWORD]
        u.GetDC.restype = W.HDC
        self._proc = WNDPROC(lambda h, msg, wp, lp: u.DefWindowProcW(h, msg, wp, lp))
        wc = WNDCLASS()
        wc.lpfnWndProc = ctypes.cast(self._proc, ctypes.c_void_p).value
        wc.hInstance = k.GetModuleHandleW(None)
        wc.lpszClassName = "PPGLoadingBanner"
        u.RegisterClassW(ctypes.byref(wc))
        self.hwnd = u.CreateWindowExW(WS_EX_TOPMOST | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE | WS_EX_LAYERED |
                                      WS_EX_TRANSPARENT, wc.lpszClassName, "Project Noble", WS_POPUP,
                                      0, 0, 1, 1, None, None, wc.hInstance, None)
        if not self.hwnd:
            raise OSError("no window")
        screen = u.GetDC(None)
        mem = g.CreateCompatibleDC(screen)
        blend = BLENDFUNCTION(0, 0, 255, 1)                                     # AC_SRC_OVER, per-pixel alpha
        cur = {"size": None, "bmp": None, "bits": None}

        def show(img, x, y):
            w, h = img.size
            if cur["size"] != (w, h):
                if cur["bmp"]:
                    g.DeleteObject(cur["bmp"])
                bi = BITMAPINFOHEADER(ctypes.sizeof(BITMAPINFOHEADER), w, -h, 1, 32, 0, 0, 0, 0, 0, 0)
                bits = ctypes.c_void_p()
                cur["bmp"] = g.CreateDIBSection(mem, ctypes.byref(bi), 0, ctypes.byref(bits), None, 0)
                if not cur["bmp"]:
                    raise OSError("no bitmap")
                g.SelectObject(mem, cur["bmp"])
                cur["size"], cur["bits"] = (w, h), bits
            data = img.convert("RGBa").tobytes("raw", "BGRa")                    # (premultiplied, as Windows wants it)
            ctypes.memmove(cur["bits"], data, len(data))
            if not u.UpdateLayeredWindow(self.hwnd, screen, ctypes.byref(W.POINT(x, y)), ctypes.byref(W.SIZE(w, h)),
                                         mem, ctypes.byref(W.POINT(0, 0)), 0, ctypes.byref(blend), 2):   # ULW_ALPHA
                raise OSError("UpdateLayeredWindow failed")

        def place():
            l, t, r, b = mcc_rect()
            sc = min(2.0, max(0.75, (b - t) / 1080.0))
            img_w = int(loading_banner.W * sc)
            return sc, l + max(0, (r - l - img_w) // 2), t + int(16 * sc)

        t0 = time.time()
        sc, x, y = place()
        show(loading_banner.frame(0.0, sc, 0.0), x, y)
        u.ShowWindow(self.hwnd, 4)                                               # SW_SHOWNOACTIVATE
        msg = W.MSG()
        last_place, closing = 0.0, None
        while True:
            while u.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
                u.TranslateMessage(ctypes.byref(msg))
                u.DispatchMessageW(ctypes.byref(msg))
            now = time.time()
            if now - last_place > 0.5:                                           # (MCC's window may move while it starts)
                sc, x, y = place()
                u.SetWindowPos(self.hwnd, -1, 0, 0, 0, 0, 0x1 | 0x2 | 0x10)      # stay on top: NOSIZE | NOMOVE | NOACTIVATE
                last_place = now
            if self._stop.is_set() and closing is None:
                closing = now
            fade = min(1.0, (now - t0) / 0.3)
            if closing is not None:
                fade = min(fade, 1.0 - (now - closing) / 0.3)
                if fade <= 0:
                    break
            show(loading_banner.frame(now - t0, sc, fade), x, y)
            time.sleep(1 / 30)
        u.DestroyWindow(self.hwnd)
        if cur["bmp"]:
            g.DeleteObject(cur["bmp"])
        g.DeleteDC(mem)
        u.ReleaseDC(None, screen)

    def _run_plain(self):
        try:
            u, g, k, WNDPROC = _api()
            try:
                u.SetProcessDPIAware()
            except Exception:
                pass
            text = self.text

            def proc(h, msg, wp, lp):
                if msg == WM_PAINT:
                    ps = PAINTSTRUCT()
                    dc = u.BeginPaint(h, ctypes.byref(ps))
                    r = W.RECT()
                    u.GetClientRect(h, ctypes.byref(r))
                    brush = g.CreateSolidBrush(0x00211A12)                       # (BGR) a dark blue-grey
                    u.FillRect(dc, ctypes.byref(r), brush)
                    g.DeleteObject(brush)
                    font = g.CreateFontW(-18, 0, 0, 0, 600, 0, 0, 0, 1, 0, 0, 4, 0, "Segoe UI")
                    old = g.SelectObject(dc, font)
                    g.SetBkMode(dc, 1)
                    g.SetTextColor(dc, 0x00FFFFFF)
                    u.DrawTextW(dc, text, -1, ctypes.byref(r), 0x25)           # DT_CENTER | DT_VCENTER | DT_SINGLELINE
                    g.SelectObject(dc, old)
                    g.DeleteObject(font)
                    u.EndPaint(h, ctypes.byref(ps))
                    return 0
                if msg == WM_DESTROY:
                    u.PostQuitMessage(0)
                    return 0
                return u.DefWindowProcW(h, msg, wp, lp)

            self._proc = WNDPROC(proc)                                           # (kept alive)
            wc = WNDCLASS()
            wc.lpfnWndProc = ctypes.cast(self._proc, ctypes.c_void_p).value
            wc.hInstance = k.GetModuleHandleW(None)
            wc.lpszClassName = "PPGLoadingTag"
            u.RegisterClassW(ctypes.byref(wc))
            left, top, right, bottom = mcc_rect()
            w, h = 760, 44
            x = left + max(0, (right - left - w) // 2)
            y = top + 14
            self.hwnd = u.CreateWindowExW(WS_EX_TOPMOST | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE | WS_EX_LAYERED |
                                          WS_EX_TRANSPARENT, wc.lpszClassName, "Project Noble", WS_POPUP,
                                          x, y, w, h, None, None, wc.hInstance, None)
            if not self.hwnd:
                return
            u.SetLayeredWindowAttributes(self.hwnd, 0, 235, 2)                    # LWA_ALPHA
            u.ShowWindow(self.hwnd, 4)                                           # SW_SHOWNOACTIVATE
            msg = W.MSG()
            while not self._stop.is_set():
                while u.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
                    u.TranslateMessage(ctypes.byref(msg))
                    u.DispatchMessageW(ctypes.byref(msg))
                # MCC's window may come and go while it starts: follow it, stay on top
                nl, nt, nr, nb = mcc_rect()
                u.SetWindowPos(self.hwnd, -1, nl + max(0, (nr - nl - w) // 2), nt + 14, w, h, 0x10 | 0x40)
                time.sleep(0.5)
            u.DestroyWindow(self.hwnd)
        except Exception:
            pass                                                                # (a missing tag must never stop the launch)


if __name__ == "__main__":                                                      # python -I loading_tag.py [seconds]
    import sys
    t = LoadingTag()
    t.start()
    print("tag up; ready:", t.wait_ready(float(sys.argv[1]) if len(sys.argv) > 1 else 5))

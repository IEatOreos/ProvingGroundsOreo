"""Thread-local storage blocks of a game DLL in MCC (Halo 3, Reach and later keep engine globals in
TLS): for every MCC thread, TEB +0x58 (ThreadLocalStoragePointer) [the DLL's _tls_index] = that
thread's block for the DLL. Read-only.

usage: python -I tls.py <dll> [hex value to find in the blocks ...]
"""
import ctypes as C
import ctypes.wintypes as W
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from memread import Game  # noqa: E402

k32 = C.windll.kernel32
ntdll = C.windll.ntdll
k32.OpenThread.restype = W.HANDLE
TH32CS_SNAPTHREAD = 0x4


class THREADENTRY32(C.Structure):
    _fields_ = [("dwSize", W.DWORD), ("cntUsage", W.DWORD), ("th32ThreadID", W.DWORD), ("th32OwnerProcessID", W.DWORD),
                ("tpBasePri", W.LONG), ("tpDeltaPri", W.LONG), ("dwFlags", W.DWORD)]


class TBI(C.Structure):
    _fields_ = [("ExitStatus", C.c_long), ("TebBaseAddress", C.c_void_p), ("UniqueProcess", C.c_void_p),
                ("UniqueThread", C.c_void_p), ("AffinityMask", C.c_size_t), ("Priority", C.c_long), ("BasePriority", C.c_long)]


def tls_index(g):
    """The DLL's _tls_index (PE TLS directory AddressOfIndex, read from the loaded image)."""
    pe = g.read(g.base, 0x1000)
    nt = struct.unpack_from("<I", pe, 0x3C)[0]
    rva = struct.unpack_from("<I", pe, nt + 0x18 + 0x70 + 9 * 8)[0]          # data directory 9: TLS
    tdir = g.read(g.base + rva, 0x28)
    addr_of_index = struct.unpack_from("<Q", tdir, 0x10)[0]
    return struct.unpack("<I", g.read(addr_of_index, 4))[0]


def blocks(g):
    """[(thread id, TLS block address)] for every thread of the game process."""
    idx = tls_index(g)
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0)
    te = THREADENTRY32()
    te.dwSize = C.sizeof(te)
    out = []
    ok = k32.Thread32First(snap, C.byref(te))
    while ok:
        if te.th32OwnerProcessID == g.pid:
            h = k32.OpenThread(0x0040, False, te.th32ThreadID)                # THREAD_QUERY_INFORMATION
            if h:
                tbi = TBI()
                if ntdll.NtQueryInformationThread(h, 0, C.byref(tbi), C.sizeof(tbi), None) == 0 and tbi.TebBaseAddress:
                    arr = g.u64(tbi.TebBaseAddress + 0x58)
                    blk = g.u64(arr + 8 * idx) if arr else None
                    if blk:
                        out.append((te.th32ThreadID, blk))
                k32.CloseHandle(h)
        ok = k32.Thread32Next(snap, C.byref(te))
    k32.CloseHandle(snap)
    return out


if __name__ == "__main__":
    g = Game(sys.argv[1])
    print("tls index", tls_index(g))
    want = [int(v, 16) for v in sys.argv[2:]]
    for tid, blk in blocks(g):
        b = g.read(blk, 0x1000) or b""
        hits = [(hex(v), hex(k)) for v in want for k in range(0, len(b) - 7, 8) if struct.unpack_from("<Q", b, k)[0] == v]
        print(tid, hex(blk), hits)

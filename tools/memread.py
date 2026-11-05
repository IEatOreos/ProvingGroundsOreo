"""Read-only look into a running MCC (anti-cheat off). Never writes to the game.

usage: python -I memread.py arrays          list Blam data arrays (name, count, size) in halo1
       python -I memread.py players         dump the players array entries (raw, for layout work)
       python -I memread.py hcm             read the HaloCheckpointManager 1.3528 Halo 1 pointers

Blam games keep game state in "data arrays": a header with a name ("players", "objects"...),
a max count, an element size and the signature 'd@t@'. Finding the header gives the table
and its element size without any static reverse engineering.
"""
import ctypes as C
import ctypes.wintypes as W
import os
import struct
import sys

PROCESS = "MCC-Win64-Shipping.exe"
GAME_DLL = "halo1.dll"
HCM_1_3528 = {"playerDatum": (0x2D9CD90, 0x4), "objectDataTable": (0x2D9CDF8, 0x34),
              "metaHeader": (0x2D9CE10, 0x0), "tickCounter": (0x2B6F5E4,)}

k32 = C.WinDLL("kernel32", use_last_error=True)
psapi = C.WinDLL("psapi", use_last_error=True)
PROCESS_VM_READ, PROCESS_QUERY_INFORMATION = 0x0010, 0x0400


class MBI(C.Structure):
    _fields_ = [("BaseAddress", C.c_void_p), ("AllocationBase", C.c_void_p), ("AllocationProtect", W.DWORD),
                ("PartitionId", W.WORD), ("RegionSize", C.c_size_t), ("State", W.DWORD),
                ("Protect", W.DWORD), ("Type", W.DWORD)]


def find_pid(name):
    arr = (W.DWORD * 4096)()
    got = W.DWORD()
    psapi.EnumProcesses(arr, C.sizeof(arr), C.byref(got))
    for pid in arr[:got.value // 4]:
        h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
        if not h:
            continue
        buf = C.create_unicode_buffer(260)
        ok = psapi.GetModuleBaseNameW(h, None, buf, 260)
        k32.CloseHandle(h)
        if ok and buf.value.lower() == name.lower():
            return pid
    return None


def refuse_if_anticheat():
    for n in ("EasyAntiCheat.exe", "EasyAntiCheat_EOS.exe", "EasyAntiCheat_Launcher.exe"):
        if find_pid(n):
            sys.exit(f"{n} is running: MCC was started with anti-cheat on. Not touching it.")


class Game:
    def __init__(s, dll=None):
        refuse_if_anticheat()
        s.pid = find_pid(PROCESS)
        if not s.pid:
            sys.exit(f"{PROCESS} is not running")
        s.h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, s.pid)
        s.dll = dll or os.environ.get("HB_GAME_DLL", GAME_DLL)     # halo1.dll, halo2.dll, ...
        s.base = s.module(s.dll)

    def module(s, name):
        mods = (C.c_void_p * 1024)()
        got = W.DWORD()
        psapi.EnumProcessModulesEx(s.h, mods, C.sizeof(mods), C.byref(got), 3)
        for m in mods[:got.value // 8]:
            buf = C.create_unicode_buffer(260)
            psapi.GetModuleBaseNameW(s.h, C.c_void_p(m), buf, 260)
            if buf.value.lower() == name.lower():
                return m
        sys.exit(f"{name} not loaded (is a Halo CE game running?)")

    def read(s, addr, n):
        buf = C.create_string_buffer(n)
        got = C.c_size_t()
        if not k32.ReadProcessMemory(s.h, C.c_void_p(addr), buf, n, C.byref(got)):
            return None
        return buf.raw[:got.value]

    def u64(s, a):
        b = s.read(a, 8)
        return struct.unpack("<Q", b)[0] if b else None

    def regions(s):
        a, mbi = 0, MBI()
        while k32.VirtualQueryEx(s.h, C.c_void_p(a), C.byref(mbi), C.sizeof(mbi)):
            if mbi.State == 0x1000 and mbi.Protect in (0x04, 0x40) and mbi.RegionSize < 1 << 30:
                yield mbi.BaseAddress, mbi.RegionSize
            a = (mbi.BaseAddress or 0) + mbi.RegionSize
            if a >= 1 << 47:
                break


def data_arrays(g):
    """Every 'd@t@' signature preceded by a plausible name: report name, max, size, address."""
    out = []
    for base, size in g.regions():
        blob = g.read(base, size)
        if not blob:
            continue
        for sig in (b"d@t@", b"@t@d"):
            i = blob.find(sig)
            while i != -1:
                best = None   # signature sits after name + counts; the offset is not known yet,
                for name_off in (0x20, 0x24, 0x28, 0x2C):   # so keep the longest clean name
                    j = i - name_off
                    if j < 0:
                        continue
                    name = blob[j:j + 32].split(b"\0")[0]
                    if 3 <= len(name) < 32 and all(48 <= c < 123 or c in b" _" for c in name):
                        if not best or len(name) > len(best[0]):
                            best = (name, j, name_off)
                if best:
                    name, j, name_off = best
                    mx, el = struct.unpack_from("<hh", blob, j + 32)
                    out.append((name.decode(), mx, el, base + j, sig.decode(), name_off))
                i = blob.find(sig, i + 4)
    return out


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "arrays"
    g = Game()
    print(f"pid {g.pid}, {g.dll} at 0x{g.base:x}")
    if cmd == "hcm":
        for k, chain in HCM_1_3528.items():
            a = g.base + chain[0]
            v = g.u64(a)
            line = f"{k}: [{GAME_DLL}+0x{chain[0]:x}] = {v and hex(v)}"
            if len(chain) > 1 and v:
                b = g.read(v + chain[1], 16)
                line += f"  then +0x{chain[1]:x}: {b.hex(' ') if b else None}"
            print(line)
    elif cmd in ("arrays", "players"):
        arrs = data_arrays(g)
        for name, mx, el, addr, sig, off in sorted(set(arrs)):
            print(f"{name:32s} max {mx:5d} size 0x{el:x}  header 0x{addr:x}  ({sig}, name at -0x{off:x})")
        if cmd == "players":
            p = next((a for a in arrs if a[0] == "players"), None)
            if p:
                hdr = g.read(p[3], 0x60)
                print("header:", hdr.hex(" "))


if __name__ == "__main__":
    main()

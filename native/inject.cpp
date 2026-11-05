// inject.exe: loads botcore.dll into a running MCC. Refuses if anti-cheat is running,
// so the bots can never be loaded into an anti-cheat (matchmaking) session.
// Refuses if a botcore is already loaded (two builds would hook the same code): restart MCC
// to load a new build, or pass --force.
// usage: inject.exe [path\to\botcore.dll] [--force]
#include <windows.h>
#include <tlhelp32.h>
#include <stdio.h>

static bool botcore_loaded(DWORD pid) {
    HANDLE snap = CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid);
    MODULEENTRY32W m{ sizeof m };
    bool found = false;
    for (BOOL ok = Module32FirstW(snap, &m); ok; ok = Module32NextW(snap, &m))
        if (!_wcsnicmp(m.szModule, L"botcore", 7)) found = true;
    CloseHandle(snap);
    return found;
}

static DWORD find(const wchar_t* exe) {
    HANDLE snap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    PROCESSENTRY32W e{ sizeof e };
    DWORD pid = 0;
    for (BOOL ok = Process32FirstW(snap, &e); ok; ok = Process32NextW(snap, &e))
        if (!_wcsnicmp(e.szExeFile, exe, wcslen(exe))) { pid = e.th32ProcessID; break; }
    CloseHandle(snap);
    return pid;
}

int wmain(int argc, wchar_t** argv) {
    wchar_t dll[MAX_PATH];
    bool force = argc > 1 && !wcscmp(argv[argc - 1], L"--force");
    if (force) argc--;
    if (argc > 1) GetFullPathNameW(argv[1], MAX_PATH, dll, nullptr);
    else { GetModuleFileNameW(nullptr, dll, MAX_PATH); wcscpy_s(wcsrchr(dll, L'\\') + 1, 64, L"botcore.dll"); }
    if (GetFileAttributesW(dll) == INVALID_FILE_ATTRIBUTES) { wprintf(L"missing %s\n", dll); return 1; }
    if (find(L"EasyAntiCheat")) { wprintf(L"Easy Anti-Cheat is running. Start MCC with anti-cheat disabled.\n"); return 2; }
    DWORD pid = find(L"MCC-Win64-Shipping.exe");
    if (!pid) { wprintf(L"MCC-Win64-Shipping.exe is not running\n"); return 3; }
    if (!force && botcore_loaded(pid)) {
        wprintf(L"a botcore DLL is already loaded in MCC: restart MCC to load another build (or --force)\n");
        return 7;
    }

    HANDLE p = OpenProcess(PROCESS_CREATE_THREAD | PROCESS_VM_OPERATION | PROCESS_VM_WRITE | PROCESS_QUERY_INFORMATION, FALSE, pid);
    if (!p) { wprintf(L"OpenProcess failed (%lu)\n", GetLastError()); return 4; }
    SIZE_T n = (wcslen(dll) + 1) * sizeof(wchar_t);
    void* mem = VirtualAllocEx(p, nullptr, n, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);
    WriteProcessMemory(p, mem, dll, n, nullptr);
    auto load = (LPTHREAD_START_ROUTINE)GetProcAddress(GetModuleHandleW(L"kernel32.dll"), "LoadLibraryW");
    HANDLE t = CreateRemoteThread(p, nullptr, 0, load, mem, 0, nullptr);
    if (!t) { wprintf(L"CreateRemoteThread failed (%lu)\n", GetLastError()); return 5; }
    WaitForSingleObject(t, 10000);
    DWORD code = 0; GetExitCodeThread(t, &code);
    VirtualFreeEx(p, mem, 0, MEM_RELEASE);
    wprintf(code ? L"botcore.dll loaded into MCC (pid %lu)\n" : L"LoadLibrary failed in MCC (pid %lu)\n", pid);
    return code ? 0 : 6;
}

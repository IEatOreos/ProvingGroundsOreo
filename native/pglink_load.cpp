// pglink_load.exe (custom, Nov 18): loads pglink.dll (the link test, native/pglink.cpp) from its own folder into a
// running MCC, beside whatever botcore is already there. As inject.exe: refuses while Easy Anti-Cheat runs. Loads it
// once a MCC run (a second load is refused: two copies would hook the same function).
#include <windows.h>
#include <tlhelp32.h>
#include <stdio.h>

static DWORD find(const wchar_t* exe) {
    HANDLE snap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    PROCESSENTRY32W e{ sizeof e };
    DWORD pid = 0;
    for (BOOL ok = Process32FirstW(snap, &e); ok; ok = Process32NextW(snap, &e))
        if (!_wcsnicmp(e.szExeFile, exe, wcslen(exe))) { pid = e.th32ProcessID; break; }
    CloseHandle(snap);
    return pid;
}

static bool loaded(DWORD pid, const wchar_t* name) {
    HANDLE snap = CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid);
    MODULEENTRY32W m{ sizeof m };
    bool found = false;
    for (BOOL ok = Module32FirstW(snap, &m); ok; ok = Module32NextW(snap, &m))
        if (!_wcsicmp(m.szModule, name)) found = true;
    CloseHandle(snap);
    return found;
}

static int done(int code) {
    wprintf(L"\nPress Enter to close.\n");
    getchar();
    return code;
}

int wmain() {
    wchar_t dll[MAX_PATH];
    GetModuleFileNameW(nullptr, dll, MAX_PATH);
    wcscpy_s(wcsrchr(dll, L'\\') + 1, 64, L"pglink.dll");
    if (GetFileAttributesW(dll) == INVALID_FILE_ATTRIBUTES) { wprintf(L"pglink.dll is missing next to this program\n"); return done(1); }
    if (find(L"EasyAntiCheat")) { wprintf(L"Easy Anti-Cheat is running. Start MCC with anti-cheat disabled.\n"); return done(2); }
    DWORD pid = find(L"MCC-Win64-Shipping.exe");
    if (!pid) { wprintf(L"MCC is not running. Start MCC first (anti-cheat off), then run this again.\n"); return done(3); }
    if (loaded(pid, L"pglink.dll")) { wprintf(L"The link test is already running in this MCC.\n"); return done(0); }
    HANDLE p = OpenProcess(PROCESS_CREATE_THREAD | PROCESS_VM_OPERATION | PROCESS_VM_WRITE | PROCESS_QUERY_INFORMATION, FALSE, pid);
    if (!p) { wprintf(L"OpenProcess failed (%lu)\n", GetLastError()); return done(4); }
    SIZE_T n = (wcslen(dll) + 1) * sizeof(wchar_t);
    void* mem = VirtualAllocEx(p, nullptr, n, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);
    WriteProcessMemory(p, mem, dll, n, nullptr);
    auto load = (LPTHREAD_START_ROUTINE)GetProcAddress(GetModuleHandleW(L"kernel32.dll"), "LoadLibraryW");
    HANDLE t = CreateRemoteThread(p, nullptr, 0, load, mem, 0, nullptr);
    if (!t) { wprintf(L"CreateRemoteThread failed (%lu)\n", GetLastError()); return done(5); }
    WaitForSingleObject(t, 10000);
    DWORD code = 0;
    GetExitCodeThread(t, &code);
    VirtualFreeEx(p, mem, 0, MEM_RELEASE);
    if (!code) { wprintf(L"MCC could not load pglink.dll (pid %lu)\n", pid); return done(6); }
    wprintf(L"The link test is running in MCC (pid %lu).\nIt writes pglink.log in this folder.\n", pid);
    return done(0);
}

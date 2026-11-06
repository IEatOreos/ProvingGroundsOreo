// ppg_window.exe: Project Proving Grounds' app window. Shows one of its local pages (the launcher, the Observer, the
// LiDAR view, the nav painter: 127.0.0.1 only) in a window of its own through Microsoft Edge WebView2, the web view
// built into Windows 10 and 11. It is not the Edge browser: no browser profile, no account sign-in, no sync, no
// extensions, no address bar. Its data (cache, settings) lives in %LOCALAPPDATA%\ProjectProvingGrounds\webview.
//
// usage: ppg_window.exe --url http://127.0.0.1:8793/ [--title "Project Proving Grounds"] [--icon <file.ico>]
//                       [--width 1040] [--height 700]
// Links to other sites open in the default browser. Without the WebView2 Runtime it says so and offers Microsoft's
// download page.
#include <windows.h>
#include <dwmapi.h>
#include <shellapi.h>
#include <shlobj.h>
#include <wrl.h>
#include <string>
#include "third_party/webview2/WebView2.h"

using Microsoft::WRL::Callback;
using Microsoft::WRL::ComPtr;

static ComPtr<ICoreWebView2Controller> g_controller;
static ComPtr<ICoreWebView2> g_view;
static std::wstring g_url = L"http://127.0.0.1:8793/", g_title = L"Project Proving Grounds", g_icon;
static int g_w = 1040, g_h = 700;

static bool local_url(const wchar_t* u) {
    return !wcsncmp(u, L"http://127.0.0.1:", 17) || !wcsncmp(u, L"http://localhost:", 17) || !wcsncmp(u, L"about:", 6);
}

static void fit(HWND hwnd) {
    if (!g_controller) return;
    RECT r;
    GetClientRect(hwnd, &r);
    g_controller->put_Bounds(r);
}

static LRESULT CALLBACK proc(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp) {
    switch (msg) {
    case WM_SIZE: fit(hwnd); return 0;
    case WM_DESTROY: PostQuitMessage(0); return 0;
    }
    return DefWindowProcW(hwnd, msg, wp, lp);
}

static void no_runtime(HWND hwnd) {
    if (MessageBoxW(hwnd, L"Project Proving Grounds needs the Microsoft Edge WebView2 Runtime, which comes with Windows 11 "
                          L"and current Windows 10. It was not found on this PC.\n\nOpen Microsoft's download page now?",
                    L"Project Proving Grounds", MB_YESNO | MB_ICONINFORMATION) == IDYES)
        ShellExecuteW(nullptr, L"open", L"https://developer.microsoft.com/microsoft-edge/webview2/", nullptr, nullptr,
                      SW_SHOWNORMAL);
}

static void parse(int argc, wchar_t** argv) {
    for (int i = 1; i + 1 < argc; i++) {
        std::wstring a = argv[i];
        if (a == L"--url") g_url = argv[++i];
        else if (a == L"--title") g_title = argv[++i];
        else if (a == L"--icon") g_icon = argv[++i];
        else if (a == L"--width") g_w = _wtoi(argv[++i]);
        else if (a == L"--height") g_h = _wtoi(argv[++i]);
    }
    if (!local_url(g_url.c_str())) g_url = L"about:blank";   // (only its own pages)
}

int WINAPI wWinMain(HINSTANCE inst, HINSTANCE, PWSTR, int show) {
    int argc = 0;
    wchar_t** argv = CommandLineToArgvW(GetCommandLineW(), &argc);
    parse(argc, argv);
    SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);
    CoInitializeEx(nullptr, COINIT_APARTMENTTHREADED);

    WNDCLASSEXW wc{ sizeof wc };
    wc.lpfnWndProc = proc;
    wc.hInstance = inst;
    wc.hCursor = LoadCursorW(nullptr, IDC_ARROW);
    wc.hbrBackground = CreateSolidBrush(RGB(14, 18, 24));
    wc.lpszClassName = L"ProjectProvingGroundsWindow";
    if (!g_icon.empty()) {
        wc.hIcon = (HICON)LoadImageW(nullptr, g_icon.c_str(), IMAGE_ICON, 0, 0, LR_LOADFROMFILE | LR_DEFAULTSIZE);
        wc.hIconSm = (HICON)LoadImageW(nullptr, g_icon.c_str(), IMAGE_ICON, 16, 16, LR_LOADFROMFILE);
    }
    RegisterClassExW(&wc);
    UINT dpi = GetDpiForSystem();
    HWND hwnd = CreateWindowExW(0, wc.lpszClassName, g_title.c_str(), WS_OVERLAPPEDWINDOW, CW_USEDEFAULT, CW_USEDEFAULT,
                                MulDiv(g_w, dpi, 96), MulDiv(g_h, dpi, 96), nullptr, nullptr, inst, nullptr);
    BOOL dark = TRUE;                                       // the title bar matches the dark pages
    DwmSetWindowAttribute(hwnd, 20 /* DWMWA_USE_IMMERSIVE_DARK_MODE */, &dark, sizeof dark);
    ShowWindow(hwnd, show);
    UpdateWindow(hwnd);
    // in front of the window that opened it (the owner, Nov 6: "the launcher draws over any pop up windows"): a window
    // started by the launcher's helper process is not let take the foreground by Windows, and opened behind the launcher.
    // Joined to the foreground window's input for the call, as Windows allows
    {
        HWND fg = GetForegroundWindow();
        DWORD fgt = fg ? GetWindowThreadProcessId(fg, nullptr) : 0, me = GetCurrentThreadId();
        if (fgt && fgt != me) AttachThreadInput(fgt, me, TRUE);
        SetWindowPos(hwnd, HWND_TOP, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW);
        BringWindowToTop(hwnd);
        SetForegroundWindow(hwnd);
        if (fgt && fgt != me) AttachThreadInput(fgt, me, FALSE);
    }

    wchar_t base[MAX_PATH] = L"";
    SHGetFolderPathW(nullptr, CSIDL_LOCAL_APPDATA, nullptr, 0, base);
    std::wstring data = std::wstring(base) + L"\\ProjectProvingGrounds\\webview";

    HRESULT hr = CreateCoreWebView2EnvironmentWithOptions(nullptr, data.c_str(), nullptr,
        Callback<ICoreWebView2CreateCoreWebView2EnvironmentCompletedHandler>(
            [hwnd](HRESULT res, ICoreWebView2Environment* env) -> HRESULT {
                if (FAILED(res) || !env) { no_runtime(hwnd); PostQuitMessage(1); return S_OK; }
                env->CreateCoreWebView2Controller(hwnd, Callback<ICoreWebView2CreateCoreWebView2ControllerCompletedHandler>(
                    [hwnd](HRESULT res2, ICoreWebView2Controller* ctl) -> HRESULT {
                        if (FAILED(res2) || !ctl) { no_runtime(hwnd); PostQuitMessage(1); return S_OK; }
                        g_controller = ctl;
                        g_controller->get_CoreWebView2(&g_view);
                        ComPtr<ICoreWebView2Controller2> c2;
                        if (SUCCEEDED(g_controller.As(&c2))) c2->put_DefaultBackgroundColor({ 255, 14, 18, 24 });
                        ComPtr<ICoreWebView2Settings> st;
                        g_view->get_Settings(&st);
                        st->put_AreDevToolsEnabled(FALSE);
                        st->put_IsStatusBarEnabled(FALSE);
                        st->put_AreDefaultContextMenusEnabled(FALSE);
                        st->put_IsWebMessageEnabled(FALSE);
                        // other sites (a link in a guide) open in the default browser, never in this window
                        g_view->add_NavigationStarting(Callback<ICoreWebView2NavigationStartingEventHandler>(
                            [](ICoreWebView2*, ICoreWebView2NavigationStartingEventArgs* a) -> HRESULT {
                                LPWSTR uri = nullptr;
                                a->get_Uri(&uri);
                                if (uri && !local_url(uri)) {
                                    a->put_Cancel(TRUE);
                                    if (!wcsncmp(uri, L"https://", 8)) ShellExecuteW(nullptr, L"open", uri, nullptr, nullptr, SW_SHOWNORMAL);
                                }
                                CoTaskMemFree(uri);
                                return S_OK;
                            }).Get(), nullptr);
                        g_view->add_NewWindowRequested(Callback<ICoreWebView2NewWindowRequestedEventHandler>(
                            [](ICoreWebView2*, ICoreWebView2NewWindowRequestedEventArgs* a) -> HRESULT {
                                LPWSTR uri = nullptr;
                                a->get_Uri(&uri);
                                a->put_Handled(TRUE);
                                if (uri && !wcsncmp(uri, L"https://", 8)) ShellExecuteW(nullptr, L"open", uri, nullptr, nullptr, SW_SHOWNORMAL);
                                CoTaskMemFree(uri);
                                return S_OK;
                            }).Get(), nullptr);
                        fit(hwnd);
                        g_view->Navigate(g_url.c_str());
                        return S_OK;
                    }).Get());
                return S_OK;
            }).Get());
    if (FAILED(hr)) { no_runtime(hwnd); return 1; }

    MSG m;
    while (GetMessageW(&m, nullptr, 0, 0) > 0) {
        TranslateMessage(&m);
        DispatchMessageW(&m);
    }
    g_controller = nullptr;
    g_view = nullptr;
    CoUninitialize();
    return 0;
}

@echo off
rem Builds native\bin\ppg_window.exe, Project Proving Grounds' app window (WebView2), with Visual Studio's C++ tools.
setlocal
set "VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
set "VSDIR="
if exist "%VSWHERE%" for /f "usebackq tokens=*" %%i in (`"%VSWHERE%" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do set "VSDIR=%%i"
if not defined VSDIR (echo Visual Studio with the C++ build tools was not found. & exit /b 1)
call "%VSDIR%\VC\Auxiliary\Build\vcvars64.bat" >nul || exit /b 1
cd /d "%~dp0"
if not exist bin mkdir bin
cl /nologo /O2 /W3 /EHsc /MT /std:c++17 /DUNICODE /D_UNICODE ppg_window.cpp third_party\webview2\x64\WebView2LoaderStatic.lib user32.lib ole32.lib shell32.lib dwmapi.lib gdi32.lib advapi32.lib version.lib /Fe:bin\ppg_window.exe /Fo:bin\ /link /SUBSYSTEM:WINDOWS || exit /b 1
echo BUILD OK bin\ppg_window.exe

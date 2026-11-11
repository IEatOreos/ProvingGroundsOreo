@echo off
rem Builds and runs pool_test.exe (Bot Matchmaking's pool checks, custom Nov 10) against the real bots_panel.cpp.
rem usage: build_pool_test.bat   (a scratch folder under bin\pool_test_run is made and emptied each run)
setlocal
set "VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
set "VSDIR="
if exist "%VSWHERE%" for /f "usebackq tokens=*" %%i in (`"%VSWHERE%" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do set "VSDIR=%%i"
if not defined VSDIR (echo Visual Studio with the C++ build tools was not found. & exit /b 1)
call "%VSDIR%\VC\Auxiliary\Build\vcvars64.bat" >nul || exit /b 1
cd /d "%~dp0"
if not exist bin mkdir bin
set IG=third_party\imgui
cl /nologo /O1 /W3 /EHsc /MT pool_test.cpp bots_panel.cpp model_view.cpp %IG%\imgui.cpp %IG%\imgui_draw.cpp %IG%\imgui_tables.cpp %IG%\imgui_widgets.cpp d3d11.lib d3dcompiler.lib dxgi.lib user32.lib winmm.lib /Fe:bin\pool_test.exe /Fo:bin\ || exit /b 1
if not exist bin\pool_test_run mkdir bin\pool_test_run
bin\pool_test.exe "%~dp0bin\pool_test_run" || exit /b 1

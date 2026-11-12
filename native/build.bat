@echo off
rem Builds botcore.dll (or botcore_<tag>.dll) and inject.exe into native\bin with Visual Studio's C++ build tools.
rem usage: build.bat [tag]   (a tag gives a fresh file name while MCC still holds an older DLL)
setlocal
rem Visual Studio with the C++ tools, wherever it is installed (vswhere ships with every Visual Studio 2017+)
set "VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
set "VSDIR="
if exist "%VSWHERE%" for /f "usebackq tokens=*" %%i in (`"%VSWHERE%" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do set "VSDIR=%%i"
if not defined VSDIR (echo Visual Studio with the C++ build tools was not found. & exit /b 1)
call "%VSDIR%\VC\Auxiliary\Build\vcvars64.bat" >nul || exit /b 1
cd /d "%~dp0"
if not exist bin mkdir bin
set NAME=botcore
if not "%1"=="" set NAME=botcore_%1
set MH=third_party\minhook\src
set IG=third_party\imgui
rem (custom, Nov 12) imgui_checks.h: a failed ImGui check is logged, not the C runtime's assert dialog that closed MCC
cl /nologo /O2 /W3 /EHsc /MT /LD /I. /DIMGUI_USER_CONFIG=\"imgui_checks.h\" botcore.cpp overlay.cpp bots_panel.cpp model_view.cpp d3dcompiler.lib h2.cpp h3.cpp reach.cpp odst.cpp h4f.cpp spawnhook.cpp report.cpp film.cpp %IG%\imgui.cpp %IG%\imgui_draw.cpp %IG%\imgui_tables.cpp %IG%\imgui_widgets.cpp %IG%\imgui_impl_dx11.cpp %IG%\imgui_impl_win32.cpp %MH%\hook.c %MH%\buffer.c %MH%\trampoline.c %MH%\hde\hde64.c d3d11.lib dxgi.lib user32.lib winmm.lib ole32.lib windowscodecs.lib /Fe:bin\%NAME%.dll /Fo:bin\ || exit /b 1
cl /nologo /O2 /W4 /EHsc /MT inject.cpp /Fe:bin\inject.exe /Fo:bin\ || exit /b 1
rem the profile view's game logos as raw pixels (tools/panel_art.py; without them the game list shows names only)
python -I ..\tools\panel_art.py
rem the 3D bots' models from MCC's own maps, once (tools/make_models.py; without them the profile view shows logos)
if not exist bin\models\h3_spartan.mdl python -I ..\tools\make_models.py
rem the profile view's armor effect sprites from the game's own particle bitmaps, once (tools/fx_art.py)
if not exist bin\art\fx_fire.rgba python -I ..\tools\fx_art.py
echo BUILD OK bin\%NAME%.dll

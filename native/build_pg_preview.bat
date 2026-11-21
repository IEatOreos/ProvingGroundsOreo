@echo off
rem Builds pg_preview.exe into native\bin (custom, Nov 16): Project Reach's screens drawn offscreen to PNGs, with the
rem real proving_grounds.cpp and bots_panel.cpp (MCC's side stood in for). usage: build_pg_preview.bat <out folder>
setlocal
set "VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
set "VSDIR="
if exist "%VSWHERE%" for /f "usebackq tokens=*" %%i in (`"%VSWHERE%" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do set "VSDIR=%%i"
if not defined VSDIR (echo Visual Studio with the C++ build tools was not found. & exit /b 1)
call "%VSDIR%\VC\Auxiliary\Build\vcvars64.bat" >nul || exit /b 1
cd /d "%~dp0"
if not exist bin\pg_preview_obj mkdir bin\pg_preview_obj
set IG=third_party\imgui
cl /nologo /O1 /W3 /EHsc /MT /I. /DPG_PREVIEW pg_preview.cpp proving_grounds.cpp bots_panel.cpp model_view.cpp armory.cpp %IG%\imgui.cpp %IG%\imgui_draw.cpp %IG%\imgui_tables.cpp %IG%\imgui_widgets.cpp %IG%\imgui_impl_dx11.cpp d3d11.lib d3dcompiler.lib dxgi.lib user32.lib winmm.lib ole32.lib windowscodecs.lib mfplat.lib mfreadwrite.lib mfuuid.lib /Fe:bin\pg_preview.exe /Fo:bin\pg_preview_obj\ || exit /b 1
if not "%~1"=="" bin\pg_preview.exe "%~1"

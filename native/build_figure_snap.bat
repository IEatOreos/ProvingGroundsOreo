@echo off
rem Builds figure_snap.exe into native\bin (custom, Nov 16): the Service Record site's still of each bot's Reach figure,
rem drawn by the bots panel's own 3D view (model_view.cpp). Visual Studio's C++ build tools, found as build.bat finds them.
setlocal
set "VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
set "VSDIR="
if exist "%VSWHERE%" for /f "usebackq tokens=*" %%i in (`"%VSWHERE%" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do set "VSDIR=%%i"
if not defined VSDIR (echo Visual Studio with the C++ build tools was not found. & exit /b 1)
call "%VSDIR%\VC\Auxiliary\Build\vcvars64.bat" >nul || exit /b 1
cd /d "%~dp0"
if not exist bin mkdir bin
if not exist bin\snap_obj mkdir bin\snap_obj
cl /nologo /O2 /W3 /EHsc /MT /I. figure_snap.cpp model_view.cpp d3d11.lib d3dcompiler.lib ole32.lib windowscodecs.lib /Fe:bin\figure_snap.exe /Fo:bin\snap_obj\ || exit /b 1
echo BUILD OK bin\figure_snap.exe

@echo off
rem Builds bink_to_mp4.exe into native\bin (custom, Nov 16): one of MCC's Bink 2 movies as an MP4 for the Service Record
rem site, decoded by MCC's own bink2w64.dll and encoded by Windows' Media Foundation. Visual Studio's C++ build tools.
setlocal
set "VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
set "VSDIR="
if exist "%VSWHERE%" for /f "usebackq tokens=*" %%i in (`"%VSWHERE%" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do set "VSDIR=%%i"
if not defined VSDIR (echo Visual Studio with the C++ build tools was not found. & exit /b 1)
call "%VSDIR%\VC\Auxiliary\Build\vcvars64.bat" >nul || exit /b 1
cd /d "%~dp0"
if not exist bin\snap_obj mkdir bin\snap_obj
cl /nologo /O2 /W3 /EHsc /MT bink_to_mp4.cpp mfplat.lib mfreadwrite.lib mfuuid.lib ole32.lib windowscodecs.lib /Fe:bin\bink_to_mp4.exe /Fo:bin\snap_obj\ || exit /b 1
echo BUILD OK bin\bink_to_mp4.exe

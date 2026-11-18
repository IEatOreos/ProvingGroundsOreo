@echo off
rem (custom, Nov 18) Builds the link test kit (native/pglink.cpp) into native\bin\linktest: pglink.dll, pglink_load.exe,
rem README.txt. A test of its own: botcore.dll is not touched.
setlocal
set "VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
set "VSDIR="
if exist "%VSWHERE%" for /f "usebackq tokens=*" %%i in (`"%VSWHERE%" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do set "VSDIR=%%i"
if not defined VSDIR (echo Visual Studio with the C++ build tools was not found. & exit /b 1)
call "%VSDIR%\VC\Auxiliary\Build\vcvars64.bat" >nul || exit /b 1
cd /d "%~dp0"
if not exist bin\linktest mkdir bin\linktest
if not exist bin\linktest\obj mkdir bin\linktest\obj
set MH=third_party\minhook\src
cl /nologo /O2 /W3 /EHsc /MT /LD /I. pglink.cpp %MH%\hook.c %MH%\buffer.c %MH%\trampoline.c %MH%\hde\hde64.c /Fe:bin\linktest\pglink.dll /Fo:bin\linktest\obj\ || exit /b 1
cl /nologo /O2 /W4 /EHsc /MT pglink_load.cpp /Fe:bin\linktest\pglink_load.exe /Fo:bin\linktest\obj\ || exit /b 1
copy /y pglink_readme.txt bin\linktest\README.txt >nul
del /q bin\linktest\pglink.exp bin\linktest\pglink.lib 2>nul
echo BUILD OK bin\linktest

@echo off
rem The Service Record with its editor (custom, Nov 17; the owner: "a permanent edit button"): starts
rem tools\service_record_edit.py in the background, with no window, unless it already runs, then opens the site.
rem   service_record_editor.cmd            start the editor if needed and open http://localhost:8766/
rem   service_record_editor.cmd /startup   start the editor only (a Startup folder shortcut, at sign-in)
setlocal
set "ROOT=%~dp0.."
powershell -NoProfile -Command "try { $c = New-Object Net.Sockets.TcpClient('127.0.0.1', 8766); $c.Close(); exit 0 } catch { exit 1 }" >nul 2>&1
if errorlevel 1 start "" /d "%ROOT%" "%ROOT%\python\pythonw.exe" -I "%ROOT%\tools\service_record_edit.py" --port 8766
if /i "%~1"=="/startup" exit /b 0
timeout /t 2 /nobreak >nul
start "" http://localhost:8766/

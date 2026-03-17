@echo off
cd /d %~dp0
start "local-preview-server" cmd /c python -m http.server 8123
ping 127.0.0.1 -n 3 >nul
start "" http://127.0.0.1:8123/index.html

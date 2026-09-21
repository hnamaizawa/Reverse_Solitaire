@echo off
setlocal
cd /d %~dp0
where py >nul 2>&1
if %errorlevel%==0 (
  py src\reverse_solitaire\app.py
) else (
  python src\reverse_solitaire\app.py
)

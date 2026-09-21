@echo off
setlocal
cd /d %~dp0

where py >nul 2>&1
if %errorlevel%==0 (
  set PYTHON=py
) else (
  where python >nul 2>&1
  if %errorlevel% neq 0 (
    echo [ERROR] Python 3 was not found in PATH.
    exit /b 1
  )
  set PYTHON=python
)

%PYTHON% -m pytest --version >nul 2>&1
if %errorlevel% neq 0 (
  echo [SETUP] pytest was not found. Installing pytest...
  %PYTHON% -m pip install pytest
  if %errorlevel% neq 0 (
    echo [ERROR] Failed to install pytest automatically.
    echo         Please run: %PYTHON% -m pip install pytest
    exit /b 1
  )
)

echo [1/2] Compile check...
%PYTHON% -m compileall -q src tests
if %errorlevel% neq 0 exit /b %errorlevel%

echo [2/2] Regression tests...
%PYTHON% -m pytest -q tests
if %errorlevel% neq 0 exit /b %errorlevel%

echo [OK] Harness passed.
exit /b 0

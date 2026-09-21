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

echo [1/2] Compile check...
%PYTHON% -m compileall -q src tests
if %errorlevel% neq 0 exit /b %errorlevel%

echo [2/2] Regression tests...
%PYTHON% -m pytest -q tests
if %errorlevel% neq 0 (
  echo.
  echo [INFO] pytest is not installed. Install it with:
  echo        %PYTHON% -m pip install pytest
  exit /b %errorlevel%
)

echo [OK] Harness passed.
exit /b 0

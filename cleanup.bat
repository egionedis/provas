@echo off
echo =================================================
echo  CLEANING PROJECT ENVIRONMENT
echo =================================================

echo.
echo [1/4] Deactivating virtual environment (if active)...
call .\.venv\Scripts\deactivate.bat 2>nul

echo.
echo [2/4] Removing old virtual environment (.venv)...
if exist .venv (
    rmdir /s /q .venv
    echo      ... Done.
) else (
    echo      ... Not found. Skipping.
)

echo.
echo [3/4] Removing build artifacts (build, dist, .egg-info)...
if exist build ( rmdir /s /q build )
if exist dist ( rmdir /s /q dist )
if exist src\provas.egg-info ( rmdir /s /q src\provas.egg-info )
echo      ... Done.

echo.
echo [4/4] Clearing pip cache...
pip cache purge
echo      ... Done.

echo.
echo =================================================
echo  CLEANUP COMPLETE!
echo  You can now create a new environment.
echo =================================================

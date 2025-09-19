@echo off
title File Hash Generator - Uninstall
echo Uninstalling File Hash Generator...
echo This will remove the virtual environment and generated files
set /p CONFIRM="Are you sure? (y/n): "
if /i "%CONFIRM%"=="y" (
    if exist venv rmdir /s /q venv
    if exist build rmdir /s /q build
    if exist dist rmdir /s /q dist
    if exist release rmdir /s /q release
    if exist "*.spec" del "*.spec"
    if exist run.bat del run.bat
    if exist build.bat del build.bat
    if exist uninstall.bat del uninstall.bat
    echo Uninstall completed
) else (
    echo Uninstall cancelled
)
pause

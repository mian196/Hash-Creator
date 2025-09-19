@echo off
setlocal enabledelayedexpansion

:: File Hash Generator & Verifier - Windows Setup Script
:: ===================================================

title File Hash Generator Setup - Windows

echo.
echo =====================================
echo  File Hash Generator ^& Verifier Setup
echo =====================================
echo  Platform: Windows
echo  Version: 2.0
echo =====================================
echo.

:: Check for Administrator privileges (optional, but recommended for some operations)
net session >nul 2>&1
if %errorLevel% == 0 (
    echo [INFO] Running with Administrator privileges
) else (
    echo [INFO] Running with standard user privileges
)

:: Check if Python is installed
echo [1/6] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH
    echo.
    echo Please install Python 3.8 or higher from:
    echo https://www.python.org/downloads/
    echo.
    echo Make sure to check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)

:: Get Python version
for /f "tokens=2" %%i in ('python --version 2^>^&1') do (
    set PYTHON_VERSION=%%i
    echo [SUCCESS] Python !PYTHON_VERSION! found
)

:: Check Python version (basic check for 3.x)
python -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)" >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python 3.8 or higher is required
    echo Current version: !PYTHON_VERSION!
    pause
    exit /b 1
)

:: Check if pip is available
echo [2/6] Checking pip availability...
python -m pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] pip is not available
    echo Please ensure pip is installed with Python
    pause
    exit /b 1
)
echo [SUCCESS] pip is available

:: Create virtual environment
echo [3/6] Creating virtual environment...
if exist "venv" (
    echo [INFO] Virtual environment already exists, removing...
    rmdir /s /q venv
)

python -m venv venv
if %errorlevel% neq 0 (
    echo [ERROR] Failed to create virtual environment
    pause
    exit /b 1
)
echo [SUCCESS] Virtual environment created

:: Activate virtual environment
echo [4/6] Activating virtual environment...
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo [ERROR] Failed to activate virtual environment
    pause
    exit /b 1
)
echo [SUCCESS] Virtual environment activated

:: Upgrade pip
echo [5/6] Upgrading pip...
python -m pip install --upgrade pip
if %errorlevel% neq 0 (
    echo [WARNING] Failed to upgrade pip, continuing...
)

:: Install requirements
echo [6/6] Installing requirements...

:: Check if requirements.txt exists
if exist "requirements.txt" (
    echo [INFO] Installing from requirements.txt...
    pip install -r requirements.txt
) else (
    echo [INFO] requirements.txt not found, installing essential packages...
    echo [INFO] Installing PyInstaller for building executables...
    pip install pyinstaller>=5.0
    
    echo [INFO] Installing optional hash libraries...
    pip install xxhash>=3.0.0
    if %errorlevel% neq 0 (
        echo [WARNING] xxhash installation failed (optional dependency)
    )
    
    pip install blake3>=0.3.0
    if %errorlevel% neq 0 (
        echo [WARNING] blake3 installation failed (optional dependency)
    )
    
    echo [INFO] Installing Pillow for icon generation...
    pip install Pillow
    if %errorlevel% neq 0 (
        echo [WARNING] Pillow installation failed (optional dependency)
    )
)

:: Check if main.py exists
if not exist "main.py" (
    echo [WARNING] main.py not found in current directory
    echo Make sure you have all the project files in this folder
)

:: Create run script
echo [INFO] Creating run script (run.bat)...
(
echo @echo off
echo title File Hash Generator ^& Verifier
echo echo Starting File Hash Generator...
echo if exist venv\ ^(
echo     echo Activating virtual environment...
echo     call venv\Scripts\activate.bat
echo ^)
echo if not exist main.py ^(
echo     echo ERROR: main.py not found
echo     pause
echo     exit /b 1
echo ^)
echo echo Launching application...
echo python main.py
echo if %%errorlevel%% neq 0 ^(
echo     echo ERROR: Application failed to start
echo     pause
echo ^)
) > run.bat

:: Create build script
echo [INFO] Creating build script (build.bat)...
(
echo @echo off
echo title File Hash Generator - Build
echo echo Building File Hash Generator executable...
echo if exist venv\ ^(
echo     echo Activating virtual environment...
echo     call venv\Scripts\activate.bat
echo ^)
echo if not exist build.py ^(
echo     echo ERROR: build.py not found
echo     pause
echo     exit /b 1
echo ^)
echo echo Starting build process...
echo python build.py %%*
echo echo Build process completed!
echo pause
) > build.bat

:: Create desktop shortcut (optional)
echo [INFO] Would you like to create a desktop shortcut? (y/n)
set /p CREATE_SHORTCUT="Create shortcut (y/n): "
if /i "!CREATE_SHORTCUT!"=="y" (
    echo [INFO] Creating desktop shortcut...
    set CURRENT_DIR=%CD%
    set SHORTCUT_PATH=%USERPROFILE%\Desktop\File Hash Generator.lnk
    powershell -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('!SHORTCUT_PATH!'); $Shortcut.TargetPath = '!CURRENT_DIR!\run.bat'; $Shortcut.WorkingDirectory = '!CURRENT_DIR!'; $Shortcut.Description = 'File Hash Generator and Verifier'; $Shortcut.Save()"
    if !errorlevel! equ 0 (
        echo [SUCCESS] Desktop shortcut created
    ) else (
        echo [WARNING] Failed to create desktop shortcut
    )
)

:: Create uninstall script
echo [INFO] Creating uninstall script...
(
echo @echo off
echo title File Hash Generator - Uninstall
echo echo Uninstalling File Hash Generator...
echo echo This will remove the virtual environment and generated files
echo set /p CONFIRM="Are you sure? (y/n): "
echo if /i "%%CONFIRM%%"=="y" ^(
echo     if exist venv rmdir /s /q venv
echo     if exist build rmdir /s /q build
echo     if exist dist rmdir /s /q dist
echo     if exist release rmdir /s /q release
echo     if exist "*.spec" del "*.spec"
echo     if exist run.bat del run.bat
echo     if exist build.bat del build.bat
echo     if exist uninstall.bat del uninstall.bat
echo     echo Uninstall completed!
echo ^) else ^(
echo     echo Uninstall cancelled
echo ^)
echo pause
) > uninstall.bat

echo.
echo =====================================
echo  Setup Completed Successfully!
echo =====================================
echo.
echo What's been installed:
echo  * Python virtual environment (venv\)
echo  * Required Python packages
echo  * Run script (run.bat)
echo  * Build script (build.bat)
echo  * Uninstall script (uninstall.bat)
echo.
echo Next steps:
echo  1. To run the application:
echo     * Double-click: run.bat
echo     * Or manually: python main.py
echo.
echo  2. To build an executable:
echo     * Double-click: build.bat
echo     * Or manually: python build.py
echo.
echo  3. To uninstall everything:
echo     * Double-click: uninstall.bat
echo.
echo The application is ready to use!
echo.

:: Offer to run the application immediately
set /p RUN_NOW="Would you like to run the application now? (y/n): "
if /i "!RUN_NOW!"=="y" (
    echo.
    echo Starting File Hash Generator...
    if exist "main.py" (
        python main.py
    ) else (
        echo ERROR: main.py not found. Please ensure all project files are present.
        pause
    )
)

echo.
echo Setup script completed. Press any key to exit...
pause >nul
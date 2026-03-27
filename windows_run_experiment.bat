@echo off
setlocal enabledelayedexpansion
REM BodyLocaliser -- Windows launcher
REM Double-click this file to install dependencies and run the experiment.
REM PsychoPy requires Python >=3.9, <3.12.

cd /d "%~dp0"

set VENV_DIR=.venv

REM -------------------------------------------------------------------
REM Step 1: Check for existing compatible venv
REM -------------------------------------------------------------------
if exist "%VENV_DIR%\Scripts\python.exe" (
    for /f "tokens=2 delims= " %%V in ('"%VENV_DIR%\Scripts\python.exe" --version 2^>^&1') do set VENV_VER=%%V
    echo !VENV_VER! | findstr /R "^3\.9\. ^3\.10\. ^3\.11\." >nul
    if not errorlevel 1 (
        echo Found existing environment with Python !VENV_VER!.
        goto :check_installed
    ) else (
        echo Existing .venv uses Python !VENV_VER!, which is not compatible.
        echo PsychoPy requires Python 3.9, 3.10, or 3.11.
        echo.
        set /p DELCHOICE="Delete the existing .venv and create a new one? [y/n] "
        if /i "!DELCHOICE!"=="y" (
            rmdir /s /q "%VENV_DIR%"
            echo Removed old environment.
        ) else (
            echo Cannot continue with an incompatible environment. Exiting.
            pause
            exit /b 1
        )
    )
)

REM -------------------------------------------------------------------
REM Step 2: Find a compatible Python on the system
REM -------------------------------------------------------------------
set PYTHON=
set FOUND_ANY=

echo.
echo Looking for Python 3.9--3.11 on this system...
echo.

REM Try the py launcher with specific versions
for %%v in (3.11 3.10 3.9) do (
    py -%%v --version >nul 2>&1
    if not errorlevel 1 (
        for /f "tokens=2 delims= " %%V in ('py -%%v --version 2^>^&1') do (
            echo   Found py -%%v ^(%%V^)
            set PYTHON=py -%%v
            set PYVER=%%V
        )
        if defined PYTHON goto :found_system_python
    )
)

REM Try generic commands
for %%c in (python3 python) do (
    where %%c >nul 2>&1
    if not errorlevel 1 (
        for /f "tokens=2 delims= " %%V in ('%%c --version 2^>^&1') do (
            set FOUND_ANY=%%c ^(%%V^)
            echo %%V | findstr /R "^3\.9\. ^3\.10\. ^3\.11\." >nul
            if not errorlevel 1 (
                echo   Found %%c ^(%%V^)
                set PYTHON=%%c
                set PYVER=%%V
                goto :found_system_python
            )
        )
    )
)

REM -------------------------------------------------------------------
REM Step 3: No compatible Python -- offer options
REM -------------------------------------------------------------------
echo.
if defined FOUND_ANY (
    echo Found !FOUND_ANY!, but PsychoPy requires 3.9, 3.10, or 3.11.
) else (
    echo No Python installation found.
)
echo.
echo PsychoPy needs Python 3.9, 3.10, or 3.11 to run.
echo.

set HAS_CONDA=0
where conda >nul 2>&1
if not errorlevel 1 set HAS_CONDA=1

echo How would you like to install a compatible Python?
echo.

set OPT=1
set OPT_CONDA=0
set OPT_INSTALLER=0
set OPT_EXIT=0

if %HAS_CONDA%==1 (
    echo   !OPT!^) Use conda to create an environment with Python 3.11 ^(recommended^)
    set OPT_CONDA=!OPT!
    set /a OPT+=1
)

echo   !OPT!^) Download and install Python 3.11 from python.org
set OPT_INSTALLER=!OPT!
set /a OPT+=1

echo   !OPT!^) Exit ^(I'll install Python myself^)
set OPT_EXIT=!OPT!

echo.

:choice_loop
set /p USERCHOICE="Enter choice [1-!OPT_EXIT!]: "

REM --- Conda ---
if "!USERCHOICE!"=="!OPT_CONDA!" if !OPT_CONDA! gtr 0 (
    echo.
    echo Creating conda environment with Python 3.11...
    conda create -y -p %VENV_DIR% python=3.11 pip -q
    if errorlevel 1 (
        echo.
        echo Conda environment creation failed.
        set /p RETRY="Would you like to try another option? [y/n] "
        if /i "!RETRY!"=="y" goto :choice_loop
        pause
        exit /b 1
    )
    echo.
    echo Conda environment created successfully.
    goto :check_installed
)

REM --- python.org installer ---
if "!USERCHOICE!"=="!OPT_INSTALLER!" (
    set PY_VER=3.11.9
    set INSTALLER=python-3.11.9-amd64.exe
    set INSTALLER_URL=https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
    set INSTALLER_PATH=%TEMP%\python-3.11.9-amd64.exe

    echo.
    echo Downloading Python 3.11.9 from python.org...
    powershell -Command "Invoke-WebRequest -Uri '!INSTALLER_URL!' -OutFile '!INSTALLER_PATH!'"

    if not exist "!INSTALLER_PATH!" (
        echo.
        echo Download failed. Check your internet connection.
        set /p RETRY="Would you like to try again? [y/n] "
        if /i "!RETRY!"=="y" goto :choice_loop
        pause
        exit /b 1
    )

    echo.
    echo Running the Python installer...
    echo "Add Python to PATH" will be enabled automatically.
    echo If a User Account Control prompt appears, click Yes to allow the install.
    echo.

    "!INSTALLER_PATH!" /passive PrependPath=1 Include_pip=1
    if errorlevel 1 (
        echo.
        echo Silent install did not complete. Opening interactive installer instead.
        echo IMPORTANT: Check "Add Python to PATH" at the bottom of the first screen.
        echo.
        "!INSTALLER_PATH!"
    )

    REM Refresh PATH
    set "PATH=C:\Python311;C:\Python311\Scripts;%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python311\Scripts;%PATH%"

    py -3.11 --version >nul 2>&1
    if not errorlevel 1 (
        set PYTHON=py -3.11
        echo.
        echo Python 3.11 installed successfully.
        goto :found_system_python
    )

    where python >nul 2>&1
    if not errorlevel 1 (
        for /f "tokens=2 delims= " %%V in ('python --version 2^>^&1') do (
            echo %%V | findstr /R "^3\.11\." >nul
            if not errorlevel 1 (
                set PYTHON=python
                echo.
                echo Python 3.11 installed successfully.
                goto :found_system_python
            )
        )
    )

    echo.
    echo Python 3.11 was not detected after installation.
    echo You may need to close this window and double-click windows_run_experiment.bat again.
    pause
    exit /b 1
)

REM --- Exit ---
if "!USERCHOICE!"=="!OPT_EXIT!" (
    echo.
    echo Install Python 3.9, 3.10, or 3.11, then run this script again.
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 0
)

echo Invalid choice. Please enter a number from 1 to !OPT_EXIT!.
goto :choice_loop

REM -------------------------------------------------------------------
REM Step 4: Create virtual environment
REM -------------------------------------------------------------------
:found_system_python
echo.
echo Will use: !PYTHON!
echo.

if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo Creating virtual environment...
    !PYTHON! -m venv %VENV_DIR%
    if errorlevel 1 (
        echo.
        echo Failed to create virtual environment.
        if %HAS_CONDA%==1 (
            set /p CONDAFB="Would you like to try using conda instead? [y/n] "
            if /i "!CONDAFB!"=="y" (
                conda create -y -p %VENV_DIR% python=3.11 pip -q
                if errorlevel 1 (
                    echo Conda also failed. Check the errors above.
                    pause
                    exit /b 1
                )
                goto :check_installed
            )
        )
        echo Try reinstalling Python 3.11 with the "Install for all users" option.
        pause
        exit /b 1
    )
)

REM -------------------------------------------------------------------
REM Step 5: Install dependencies
REM -------------------------------------------------------------------
:check_installed
call %VENV_DIR%\Scripts\activate.bat

if not exist "%VENV_DIR%\.installed" (
    echo.
    echo Installing PsychoPy and dependencies (this may take a few minutes^)...
    echo.
    pip install --upgrade pip -q 2>nul
    pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo Dependency installation failed.
        echo.
        set /p RETRYPIP="Would you like to retry? [y/n] "
        if /i "!RETRYPIP!"=="y" (
            pip install -r requirements.txt
            if errorlevel 1 (
                echo.
                echo Installation failed again. Check the error messages above.
                pause
                exit /b 1
            )
        ) else (
            echo You can try running this script again later.
            pause
            exit /b 1
        )
    )
    echo. > %VENV_DIR%\.installed
    echo.
    echo Dependencies installed successfully.
)

REM -------------------------------------------------------------------
REM Step 6: Run the experiment
REM -------------------------------------------------------------------
:run_experiment
echo.
echo Starting BodyLocaliser...
echo ---
python src\main.py

echo.
echo Experiment finished.
echo.
set /p RERUN="Run the experiment again? [y/n] "
if /i "!RERUN!"=="y" goto :run_experiment

echo Done.
pause

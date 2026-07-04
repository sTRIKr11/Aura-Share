@echo off
title AuraShare V4.0 Universal Launcher
color 0A

echo ===================================================
echo     AuraShare V4.0 - Automated Setup ^& Launch
echo ===================================================
echo.

if not exist venv\ (
    echo First-time setup detected on this device. 
    echo Building virtual environment with Python 3.11...
    py -3.11 -m venv venv
    
    echo Activating secure environment and installing libraries...
    call venv\Scripts\activate
    python -m pip install --upgrade pip
    pip install -r requirements.txt
) else (
    echo Existing environment found. Activating...
    call venv\Scripts\activate
)

echo.
echo All systems nominal. Launching AuraShare UI...
echo ===================================================
python main.py

pause
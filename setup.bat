@echo off
echo ===========================================
echo   Setting up Redot Gambling Bot...
echo ===========================================

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH.
    pause
    exit /b 1
)

if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing requirements...
python -m pip install --upgrade pip
pip install -r requirements.txt

if not exist ".env" (
    echo Creating .env from .env.example...
    copy .env.example .env
    echo Please edit .env with your Discord Bot Token and Channel IDs!
)

echo.
echo Setup complete! Run 'venv\Scripts\activate ^&^& python bot.py' to start.
pause

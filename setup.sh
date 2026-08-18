#!/usr/bin/env bash
set -e

echo "==========================================="
echo "  Setting up Redot Gambling Bot..."
echo "==========================================="

if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed or not in PATH."
    exit 1
fi

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing requirements..."
pip install --upgrade pip
pip install -r requirements.txt

if [ ! -f ".env" ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo "Please edit .env with your Discord Bot Token and Channel IDs!"
fi

echo ""
echo "Setup complete! Run 'source venv/bin/activate && python bot.py' to start."

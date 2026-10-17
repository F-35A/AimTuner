@echo off
cd /d "%~dp0"
python -c "import pygame, numpy" 2>nul || python -m pip install pygame numpy
python app.py
if errorlevel 1 pause

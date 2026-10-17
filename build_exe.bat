@echo off
cd /d "%~dp0"
python -m pip install pygame numpy pyinstaller
pyinstaller --noconfirm --onefile --windowed --name AimTuner --icon icon.ico --add-data "icon.png;." --exclude-module fakeplat app.py
echo Done: dist\AimTuner.exe
pause

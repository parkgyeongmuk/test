@echo off
chcp 65001 >nul
cd /d "%~dp0"
python png2jpg.py %*
if errorlevel 1 pause

@echo off
title Running Free Video Downloader Pro
python "%~dp0free_downloader_pro.py"
if %errorlevel% neq 0 (
    echo.
    echo An error occurred while running the downloader.
    echo Please make sure Python and PyQt5 are installed correctly.
    pause
)

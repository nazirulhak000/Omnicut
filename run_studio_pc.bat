@echo off
chcp 65001 > nul
title OmniCut Pro Studio - PC ^& Mobile Studio
cd /d "%~dp0"
if exist .venv\Scripts\python.exe (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)
%PYTHON_EXE% tools\run_studio_pc.py
pause

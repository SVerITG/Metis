@echo off
title Metis — Installer
echo.
echo  Metis Research Cortex
echo  Starting installer...
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"

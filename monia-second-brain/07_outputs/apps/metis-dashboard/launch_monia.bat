@echo off
REM ============================================================
REM Monia Dashboard Launcher
REM Double-click to open the dashboard in your browser.
REM No RStudio needed. Keep this window open while using it.
REM ============================================================

set APP_DIR=%~dp0

REM Find Rscript.exe — scans common R installation locations
set RSCRIPT=
for /d %%v in ("C:\Program Files\R\R-4.*") do (
  if exist "%%v\bin\Rscript.exe" set RSCRIPT=%%v\bin\Rscript.exe
)
if "%RSCRIPT%"=="" (
  for /f "tokens=*" %%i in ('where Rscript.exe 2^>nul') do set RSCRIPT=%%i
)
if "%RSCRIPT%"=="" (
  echo ERROR: Rscript.exe not found.
  echo Please install R from https://cran.r-project.org/
  pause
  exit /b 1
)

echo Monia Dashboard
echo ---------------
echo App:    %APP_DIR%
echo R:      %RSCRIPT%
echo URL:    http://localhost:3838
echo.
echo Opening in browser... (close this window to stop the dashboard)
echo.

"%RSCRIPT%" "%APP_DIR%launch.R"
pause

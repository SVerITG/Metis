@echo off
REM Metis Launcher — double-click to start the dashboard
REM Opens the browser to http://127.0.0.1:8000

REM Start the Python dashboard (in background, via WSL)
start "" wsl.exe -d Ubuntu-24.04 -- bash -c "cd '/mnt/c/Users/sverschaeve/OneDrive - ITG/Documents/7. Software/Research Cortex/metis/system/app-py' && METIS_RC_ROOT='/mnt/c/Users/sverschaeve/OneDrive - ITG/Documents/7. Software/Research Cortex/metis' PYTHONPATH='/home/sverschaeve/.local/share/metis-mcp/.venv/lib/python3.12/site-packages' /usr/bin/python3.12 -m uvicorn main:app --host 127.0.0.1 --port 8000 2>&1 &"

REM Wait for server to start, then open browser
timeout /t 3 /nobreak >nul
start "" http://127.0.0.1:8000

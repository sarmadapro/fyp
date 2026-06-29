@echo off
echo Stopping all VocalizeWeb services...

for %%P in (8000 8001 8002 5173 3000) do (
    for /f "tokens=5" %%i in ('netstat -aon ^| findstr ":%%P " ^| findstr "LISTENING"') do (
        echo Killing PID %%i on port %%P
        taskkill /PID %%i /F >nul 2>&1
    )
)

echo All services stopped.

@echo off
title WEPClaude Web UI
echo.
echo   Starting WEPClaude Web UI ...
echo.
cd /d "%~dp0"
node webui\server.mjs
pause

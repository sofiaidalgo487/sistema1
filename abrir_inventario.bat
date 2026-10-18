@echo off
setlocal
cd /d "%~dp0"

REM Iniciar Flask usando el Python disponible en Windows
start "Servidor Flask - Inventario" cmd /k "python app.py"

REM Esperar unos segundos para que el servidor arranque y abrir Chrome
timeout /t 3 /nobreak >nul
start "" "http://127.0.0.1:5000"

endlocal

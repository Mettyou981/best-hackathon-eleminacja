@echo off
setlocal
cd /d "%~dp0"

title SmartPlanner - Podsieciowe Maskarady

echo ========================================================
echo   Uruchamianie SmartPlanner...
echo ========================================================
echo.

if exist "%~dp0.venv\Scripts\activate.bat" (
    echo [INFO] Aktywacja srodowiska wirtualnego .venv...
    call "%~dp0.venv\Scripts\activate.bat"
)

echo [INFO] Uruchamianie aplikacji (python main.py)...
python "%~dp0main.py"
set APP_EXIT_CODE=%ERRORLEVEL%

if %APP_EXIT_CODE% neq 0 (
    echo.
    echo [OSTRZEZENIE] Proba uruchomienia przez py -3 main.py...
    py -3 "%~dp0main.py"
    set APP_EXIT_CODE=%ERRORLEVEL%
)

if %APP_EXIT_CODE% neq 0 (
    echo.
    echo ========================================================
    echo   [BLAD] Aplikacja zakonczyla dzialanie z bledem.
    echo ========================================================
    echo.
    pause
) else (
    echo [INFO] Aplikacja zakonczona pomyslnie.
)
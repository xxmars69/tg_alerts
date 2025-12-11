@echo off
echo ====================================
echo   OLX Telegram Alert - Local Run
echo ====================================
echo.

REM Verifică dacă există fișierul .env
if not exist .env (
    echo [EROARE] Fișierul .env nu există!
    echo.
    echo Creează un fișier .env din .env.example:
    echo   copy .env.example .env
    echo.
    echo Apoi editează .env și completează valorile.
    pause
    exit /b 1
)

echo [INFO] Încărcare variabile de mediu din .env...
echo.

REM Încarcă variabilele din .env și rulează spider-ul
for /f "tokens=1,* delims==" %%a in (.env) do (
    if not "%%a"=="" (
        if not "%%a"=="#" (
            set "%%a=%%b"
        )
    )
)

REM Rulează spider-ul
echo [INFO] Rulare spider...
scrapy crawl watch -s LOG_LEVEL=INFO

echo.
echo [INFO] Rulare finalizată!
pause

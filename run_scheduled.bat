@echo off
REM Script pentru rulare programată (Task Scheduler)
REM Setează calea completă aici
cd /d "C:\Users\mariu\olx-telegram-alert"

REM Încarcă variabilele din .env
for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
    if not "%%a"=="" if not "%%a"=="#" (
        set "%%a=%%b"
    )
)

REM Rulează spider-ul (fără output verbose pentru task scheduler)
scrapy crawl watch -s LOG_LEVEL=WARNING > nul 2>&1

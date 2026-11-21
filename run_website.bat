@echo off
chcp 65001 > nul
title AI 유튜브 다국어 목소리 더빙 스튜디오
echo ========================================================
echo  🌐 AI 유튜브 다국어 목소리 더빙 웹사이트 구동 중...
echo ========================================================
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] 가상 환경(.venv)을 찾을 수 없습니다.
    pause
    exit /b 1
)

echo 웹 서버를 시작합니다.
echo 브라우저 접속 주소: http://127.0.0.1:8000
echo.

start "" "http://127.0.0.1:8000"
.\.venv\Scripts\python.exe server.py
pause


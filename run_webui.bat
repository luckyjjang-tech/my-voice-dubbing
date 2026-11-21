@echo off
chcp 65001 > nul
echo ========================================================
echo  🎙️ AI 유튜브 다국어 목소리 더빙 스튜디오 시작 중...
echo ========================================================
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] 가상 환경(.venv)을 찾을 수 없습니다.
    pause
    exit /b 1
)

echo 가상환경 활성화 및 웹 UI 서버 구동 중...
echo 브라우저가 자동으로 열리지 않을 경우 아래 주소로 접속하세요:
echo http://127.0.0.1:7860
echo.

.\.venv\Scripts\python.exe app.py
pause


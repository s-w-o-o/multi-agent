@echo off
title INTERX Multi-Agent System Runner
echo ===================================================
echo   INTERX Ultimate Multi-Agent System (v3) Launcher
echo ===================================================
echo.

:: Check Python installation
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python이 설치되어 있지 않거나 환경 변수(PATH)에 등록되어 있지 않습니다.
    echo 설치 가이드(docs/INSTALL_GUIDE.md)를 참고하여 Python을 설치해 주세요.
    echo.
    pause
    exit /b
)

echo [INFO] 필요한 패키지를 자동으로 점검 및 설치합니다...
python -m pip install --upgrade pip
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo [WARNING] 일부 라이브러리 설치 중 오류가 발생했습니다.
    echo 이미 설치되어 있다면 정상 실행될 수 있으니 실행을 진행합니다.
    echo.
)

echo [INFO] INTERX 에이전트 시스템을 실행합니다...
echo 브라우저 창이 자동으로 열리지 않으면 http://localhost:8501로 접속하세요.
echo.
streamlit run app.py

pause

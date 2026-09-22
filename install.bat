@echo off
setlocal enabledelayedexpansion

title Sentinel AI Installer
echo ==========================================
echo        Welcome to Sentinel AI Setup
echo ==========================================
echo.

:: Define the GitHub repository URL (User will need to update this with their actual repo)
set "REPO_ZIP_URL=https://github.com/YOUR_GITHUB_USERNAME/sentinel-ai/archive/refs/heads/main.zip"
set "INSTALL_DIR=%USERPROFILE%\Desktop\SentinelAI"

:: Check if the directory already exists
if exist "%INSTALL_DIR%" (
    echo Sentinel AI is already installed on your Desktop at %INSTALL_DIR%.
    echo To reinstall, please delete that folder first.
    pause
    exit /b
)

echo [1/5] Downloading Sentinel AI...
powershell -Command "Invoke-WebRequest -Uri '%REPO_ZIP_URL%' -OutFile 'SentinelAI.zip'"
if not exist "SentinelAI.zip" (
    echo Failed to download the code. Please check your internet connection or the repository URL.
    pause
    exit /b
)

echo [2/5] Extracting files...
powershell -Command "Expand-Archive -Path 'SentinelAI.zip' -DestinationPath '%USERPROFILE%\Desktop\TempSentinel'"
del "SentinelAI.zip"

:: Move the extracted folder to the final destination (handles the nested main folder from GitHub)
for /d %%I in ("%USERPROFILE%\Desktop\TempSentinel\*") do (
    move "%%I" "%INSTALL_DIR%" >nul
)
rd /s /q "%USERPROFILE%\Desktop\TempSentinel"

cd /d "%INSTALL_DIR%"

echo [3/5] Checking for uv package manager...
where uv >nul 2>&1
if %errorlevel% neq 0 (
    echo uv is not installed. Installing uv...
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    :: Add uv to the current path session
    set "PATH=%USERPROFILE%\.cargo\bin;%PATH%"
) else (
    echo uv is already installed.
)

echo.
echo ==========================================
echo [4/5] Setup your Gemini API Key
echo ==========================================
echo You can get a free API key from: https://aistudio.google.com/app/apikey
echo.
set /p API_KEY="Please paste your Gemini API Key here and press Enter: "

:: Write to .env file
echo GEMINI_API_KEY="%API_KEY%" > .env
echo.
echo API Key saved successfully!

echo [5/5] Launching Sentinel AI...
echo (This may take a moment the first time as it downloads dependencies...)
uv run streamlit run ui.py

pause

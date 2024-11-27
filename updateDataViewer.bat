@echo off

REM Check if Git is installed
echo Checking if Git is installed...
git --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Git is not installed.
    echo Please install Git from the following link: https://git-scm.com/downloads
    echo Once installed, re-run this script.
    pause
    exit /b
)

REM Set the repository URL
set REPO_URL=https://github.com/CalebH1208/MR_Data_Visualization_Tool.git

REM Check if the current directory is a Git repository
echo Checking if the current directory is a Git repository...
git rev-parse --is-inside-work-tree >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Current directory is not a Git repository. Cloning the repository here...
    git clone %REPO_URL% . 
    IF %ERRORLEVEL% NEQ 0 (
        echo Failed to clone repository. Please check the URL or your network connection.
        pause
        exit /b
    )
) else (
    echo Current directory is a Git repository. Pulling the latest changes...
    git pull
    IF %ERRORLEVEL% NEQ 0 (
        echo Failed to pull the latest changes. Please check your repository configuration.
        pause
        exit /b
    )
)

echo Operation completed successfully.
timeout /t 2 /nobreak >nul
exit

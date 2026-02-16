@echo off
setlocal EnableExtensions
chcp 65001 > nul
cd /d "%~dp0"

set "WORKLOG=docs\ops\CODEX_WORKLOG.md"
set "REPO_URL=https://github.com/hyungjin-J/AI_Chat_for_CS.git"
set "COMMIT_MESSAGE=chore: bootstrap backend frontend infra and cmd automation"

>> "%WORKLOG%" echo ## [%date% %time%] 99_git_init_commit_push.cmd
>> "%WORKLOG%" echo - Step: git init -> remote add -> commit -> push
>> "%WORKLOG%" echo - CMD: git init / git branch -M main / git remote add origin %REPO_URL% / git add . / git commit / git push

git rev-parse --is-inside-work-tree > nul 2>&1
if errorlevel 1 (
    git init
    if errorlevel 1 (
    echo [ERROR] git init failed
    >> "%WORKLOG%" echo - Result: failed; git init
        exit /b 1
    )
) else (
    echo [INFO] existing git repository detected
)

git branch -M main
if errorlevel 1 (
    echo [ERROR] git branch -M main failed
    >> "%WORKLOG%" echo - Result: failed; git branch -M main
    exit /b 1
)

git remote remove origin > nul 2>&1
git remote add origin "%REPO_URL%"
if errorlevel 1 (
    echo [ERROR] failed to set remote origin
    >> "%WORKLOG%" echo - Result: failed; remote add
    exit /b 1
)

git add .
if errorlevel 1 (
    echo [ERROR] git add failed
    >> "%WORKLOG%" echo - Result: failed; git add
    exit /b 1
)

git diff --cached --quiet
if errorlevel 1 (
    git commit -m "%COMMIT_MESSAGE%"
    if errorlevel 1 (
        echo [ERROR] git commit failed; check user.name/user.email
        >> "%WORKLOG%" echo - Result: failed; git commit
        >> "%WORKLOG%" echo - Manual CMD: git config user.name "YOUR_NAME" ^&^& git config user.email "YOUR_EMAIL"
        exit /b 1
    )
) else (
    echo [INFO] no staged changes to commit.
)

git push -u origin main
if errorlevel 1 (
    echo [WARN] git push failed. check authentication/permission.
    >> "%WORKLOG%" echo - Result: partial failure; git push
    >> "%WORKLOG%" echo - Cause/Fix: check auth token/permission/protection rules
    >> "%WORKLOG%" echo - Manual CMD: git push -u origin main
    exit /b 1
)

>> "%WORKLOG%" echo - Commit message: %COMMIT_MESSAGE%
>> "%WORKLOG%" echo - Result: success
echo [OK] 99_git_init_commit_push done
exit /b 0

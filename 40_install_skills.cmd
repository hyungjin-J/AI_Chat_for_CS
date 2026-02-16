@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 > nul
cd /d "%~dp0"

set "WORKLOG=docs\ops\CODEX_WORKLOG.md"
set "CODEX_HOME=%CD%\.agents"

if not exist ".agents" mkdir ".agents"
if not exist ".agents\skills" mkdir ".agents\skills"

>> "%WORKLOG%" echo ## [%date% %time%] 40_install_skills.cmd
>> "%WORKLOG%" echo - Step: install P0+P1 skills
>> "%WORKLOG%" echo - CMD: npx skills add ... --skill ...
>> "%WORKLOG%" echo - CODEX_HOME: %CODEX_HOME%

set /a OK_COUNT=0
set /a FAIL_COUNT=0

call :runSkill "npx skills add https://github.com/yanko-belov/code-craft --skill idempotency"
call :runSkill "npx skills add https://github.com/patricio0312rev/skills --skill rate-limiting-abuse-protection"
call :runSkill "npx skills add https://github.com/patricio0312rev/skills --skill redis-patterns"
call :runSkill "npx skills add https://github.com/patricio0312rev/skills --skill observability-setup"
call :runSkill "npx skills add https://github.com/vasilyu1983/ai-agents-public --skill software-backend"
call :runSkill "npx skills add https://github.com/patricio0312rev/skills --skill guardrails-safety-filter-builder"
call :runSkill "npx skills add https://github.com/patricio0312rev/skills --skill webhook-receiver-hardener"
call :runSkill "npx skills add https://github.com/laguagu/claude-code-nextjs-skills --skill postgres-semantic-search"
call :runSkill "npx skills add https://github.com/jackspace/claudeskillz --skill openai-api"
call :runSkill "npx skills add https://github.com/jeffallan/claude-skills --skill rag-architect"
call :runSkill "npx skills add https://github.com/yonatangross/orchestkit --skill dashboard-patterns"
call :runSkill "npx skills add https://github.com/jmerta/codex-skills --skill release-notes"
call :runSkill "npx skills add https://github.com/drillan/speckit-gates --skill release-check"
call :runSkill "npx skills add https://github.com/patricio0312rev/skills --skill skill-creator"

>> "%WORKLOG%" echo - Installed OK: !OK_COUNT!
>> "%WORKLOG%" echo - Installed FAIL: !FAIL_COUNT!

if exist ".agents\skills" (
    >> "%WORKLOG%" echo - .agents\skills tree:
    for /f "delims=" %%F in ('dir /b ".agents\skills" 2^>nul') do (
        >> "%WORKLOG%" echo   - %%F
    )
)

if !FAIL_COUNT! gtr 0 (
    >> "%WORKLOG%" echo - Result: partial failure
    >> "%WORKLOG%" echo - Cause/Fix: network issue or missing npx skills CLI. retry failed items manually.
    >> "%WORKLOG%" echo - Manual CMD: set CODEX_HOME=%%CD%%\.agents ^&^& npx skills add ^<repo_url^> --skill ^<skill_name^>
    echo [WARN] some skills failed: !FAIL_COUNT!
) else (
    >> "%WORKLOG%" echo - Result: success
    echo [OK] all skills installed
)

>> "%WORKLOG%" echo - Next: run 50_generate_gitignore.cmd
exit /b 0

:runSkill
set "COMMAND_TO_RUN=%~1"
echo [RUN] !COMMAND_TO_RUN!
cmd /c "!COMMAND_TO_RUN!"
if errorlevel 1 (
    set /a FAIL_COUNT+=1
    >> "%WORKLOG%" echo - FAIL: !COMMAND_TO_RUN!
) else (
    set /a OK_COUNT+=1
    >> "%WORKLOG%" echo - OK: !COMMAND_TO_RUN!
)
exit /b 0

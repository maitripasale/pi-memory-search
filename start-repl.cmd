@echo off
setlocal
cd /d "%~dp0"
set "PI_CODING_AGENT_DIR=%~dp0.pi_isolated"
set "PI_OFFLINE=1"
node "%~dp0node_modules\@earendil-works\pi-coding-agent\dist\cli.js" --no-context-files --no-extensions --no-skills --no-prompt-templates -e "%~dp0extensions\jupyter-repl.ts" --tools read,ls,find,grep,python_cell,python_history,python_reset --provider particle-ai --model glm-5.3-flash %*
endlocal

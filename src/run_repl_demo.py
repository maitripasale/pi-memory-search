"""Run a scripted notebook demonstration through Pi (one model session)."""
import json
import os
import subprocess
import uuid
from pathlib import Path

root = Path(__file__).resolve().parents[1]
folder = root / 'results' / ('repl_demo_' + uuid.uuid4().hex[:8])
folder.mkdir(parents=True)
env = os.environ.copy()
env['PI_CODING_AGENT_DIR'] = str(root / '.pi_isolated')
env['PI_OFFLINE'] = '1'
prompt = """Demonstrate the persistent Python notebook with exactly these steps:
1. Call python_cell to define docs={'guide.txt':'Set cache-timeout to 30 seconds.', 'other.txt':'Enable logging.'} and query='cache_timeout'. Search docs for the exact query and print the matches. It should be empty.
2. In a SEPARATE python_cell call, reuse docs and query without redefining them. Normalize hyphens to underscores in both query and document text. Search again and print matching filenames.
3. Call python_history to review those two attempts.
4. In python_cell, save search_result.json containing {"matches": ["guide.txt"], "lesson": "Check naming variants when an exact search returns no results."}, using the actual matches from step 2. Print that variables persisted.
Finally summarize what happened. This is a scripted tool demonstration, not a memory-effectiveness experiment."""
cmd = ['node', str(root/'node_modules/@earendil-works/pi-coding-agent/dist/cli.js'),
       '-p','--mode','json','--no-session','--no-context-files','--no-extensions','--no-skills','--no-prompt-templates',
       '-e',str(root/'extensions/jupyter-repl.ts'),'--tools','python_cell,python_history,python_reset',
       '--provider','particle-ai','--model','glm-5.3-flash',prompt]
result = subprocess.run(cmd,cwd=folder,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180)
(folder/'events.jsonl').write_text(result.stdout,encoding='utf-8')
(folder/'stderr.txt').write_text(result.stderr,encoding='utf-8')
calls=[]
errors=[]
for line in result.stdout.splitlines():
    try: event=json.loads(line)
    except ValueError: continue
    if event.get('type')=='message_end':
        msg=event.get('message',{})
        if msg.get('role')=='assistant':
            calls += [c.get('name') for c in msg.get('content',[]) if c.get('type')=='toolCall']
        if msg.get('role')=='toolResult' and msg.get('isError'):
            errors.append(msg.get('content'))
output=folder/'search_result.json'
passed=output.exists() and json.loads(output.read_text()).get('matches')==['guide.txt'] and calls.count('python_cell')>=3 and 'python_history' in calls and not errors
summary={'passed':passed,'returncode':result.returncode,'tools_called':calls,'tool_errors':errors,'folder':str(folder),
         'notebooks':[str(p) for p in (folder/'notebooks').glob('*.ipynb')],
         'limitation':'Scripted demonstration: no cross-session memory or measured learning effect.'}
(folder/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps(summary,indent=2))
if not passed:
    print(result.stderr[-2500:])
    raise SystemExit(1)

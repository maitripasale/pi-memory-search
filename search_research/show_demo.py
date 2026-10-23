"""Print saved pilot artifacts for a meeting. No model calls."""
import argparse
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--run',type=Path);a=p.parse_args()
folders=sorted((HERE/'runs').glob('*'),key=lambda p:p.stat().st_mtime,reverse=True)
folder=a.run or next((x for x in folders if (x/'report.json').exists() and json.loads((x/'report.json').read_text(encoding='utf-8'))['summary']),None)
if not folder:raise SystemExit('No evaluation report is available yet.')
print('SAVED EXPERIMENT:',folder)
print('\nMEMORY CANDIDATES:')
for m in json.loads((folder/'memories.json').read_text(encoding='utf-8')):
    print(m['type']+': '+m['lesson']);print('  Evidence:',m['evidence'])
print('\n'+(folder/('AUDITED_REPORT.md' if (folder/'AUDITED_REPORT.md').exists() else 'REPORT.md')).read_text(encoding='utf-8'))
print('\nINSPECT THESE FILES:')
for x in sorted(folder.glob('evaluation_*/run.json')):
    r=json.loads(x.read_text(encoding='utf-8'))
    if (x.parent/'evaluation.audited.json').exists(): r['evaluation']=json.loads((x.parent/'evaluation.audited.json').read_text(encoding='utf-8'))
    print(r['task_id'],r['condition'],'injected=',r['retrieval']['ids'],'calls=',len(r['calls']),'passed=',r['evaluation']['success'])
    for c in r['calls'][:1]:print('  First action:',str(c.get('arguments'))[:500])
    print('  Notebook folder:',x.parent/'notebooks')

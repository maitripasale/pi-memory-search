"""Uniform post-run evidence correction; preserves original trajectories and scores."""
import argparse,copy,json,re,shutil
from pathlib import Path
import experiment as e

def audited_evaluation(task,response,corpus):
 result=e.evaluate(task,response,corpus)
 if task['family']!='precedence':return result
 # The system requires a calculation/merge rule citation for a derived field.
 # Accept the exact rule only with the separately grounded requested inputs.
 anchors=[]
 for p in (corpus/task['id']).glob('*.ipynb'):
  for i,c in enumerate(e.load(p)['cells']):
   text=''.join(c['source'])
   if text.startswith('# Merge rules\n'):
    anchors.append((p.relative_to(corpus).as_posix(),i,'Later enabled matching-region values replace earlier ones. Disabled overlays do not apply.'))
 if len(anchors)!=1:raise ValueError('Expected one independently verified merge rule')
 file,cell,quote=anchors[0]
 other=copy.deepcopy(task)
 other['facts']['effective_limit'].update(file=file,cell=cell,quote=quote)
 alternative=e.evaluate(other,response,corpus)
 inputs=all(result['fields'][k]['passed'] for k in ('base_limit','region_limit'))
 if inputs and alternative['fields']['effective_limit']['passed']:
  result['fields']['effective_limit']=alternative['fields']['effective_limit']
 result['success']=all(x['passed'] for x in result['fields'].values())
 result['grounded_accuracy']=sum(x['passed'] for x in result['fields'].values())/len(result['fields'])
 return result

def main():
 p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);a=p.parse_args();out=a.run.resolve()
 tasks={t['id']:t for t in e.load(e.HERE/'dataset_v3/tasks.json')['tasks']}
 audited=[];practice=[];changes=[]
 for path in sorted(out.glob('*/run.json')):
  r=e.load(path)
  if r.get('task_id') not in tasks:continue
  corrected=audited_evaluation(tasks[r['task_id']],r['response'],path.parent/'corpus')
  if r['timeout'] or r['returncode']!=0 or r['model_errors']:corrected['success']=False
  if corrected!=r['evaluation']:changes.append({'run_id':r['run_id'],'original':r['evaluation'],'audited':corrected})
  e.save(path.parent/'evaluation.audited.json',corrected)
  r['evaluation']=corrected
  (practice if r['split']=='practice' else audited).append(r)
 dest=out/'audit';dest.mkdir(exist_ok=True)
 reviewed=e.load(out/'reviewer/run.json');e.report(dest,audited,practice,reviewed)
 shutil.copyfile(dest/'report.json',out/'audited_report.json');shutil.copyfile(dest/'REPORT.md',out/'AUDITED_REPORT.md')
 counts={}
 for c in e.CONDITIONS:
  group=[r for r in audited if r['condition']==c];types={}
  for r in group:
   for t in r['results']:
    if not t.get('isError'):continue
    text='\n'.join(x.get('text','') for x in t.get('content',[]) if x.get('type')=='text')
    names=re.findall(r'(?:^|\n)([A-Za-z]+Error):',text)
    for name in names or ['tool_error']:types[name]=types.get(name,0)+1
  counts[c]=types
 note='Evidence audit v3.0.1: accept the documented merge rule for derived override results when requested inputs are grounded. Original scores remain in run.json and REPORT.md. One repetition per condition; synthetic near-transfer pilot, not strong causal evidence.'
 e.save(out/'audit.json',{'summary':note,'changed_scores':changes,'error_types':counts})
 with (out/'AUDITED_REPORT.md').open('a',encoding='utf-8') as f:f.write('\n\n## Evidence scoring correction\n\n'+note+'\n')
 print(json.dumps({'summary':e.load(out/'audited_report.json')['summary'],'error_types':counts,'corrected_runs':len(changes)},indent=2))
if __name__=='__main__':main()

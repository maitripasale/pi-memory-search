"""No-memory difficulty calibration. Resumable; no memory writing/review."""
import argparse,json,uuid
from pathlib import Path
import experiment as e
from memory import MemoryStore

def main():
    p=argparse.ArgumentParser();p.add_argument('--limit',type=int,default=18);p.add_argument('--resume',type=Path);a=p.parse_args()
    e.DATA=e.HERE/'dataset_v2'
    data=e.load(e.DATA/'tasks.json')
    out=a.resume.resolve() if a.resume else e.HERE/'runs'/('harder_baseline_'+uuid.uuid4().hex[:10])
    out.mkdir(parents=True,exist_ok=True)
    e.save(out/'manifest.json',{'dataset_version':data['version'],'dataset_sha256':e.digest(e.DATA/'tasks.json'),'corpus_manifest_sha256':e.digest(e.DATA/'manifest.json'),'provider':'particle-ai','model':'glm-5.3-flash','condition':'none','purpose':'difficulty calibration; no memory benefit claim','code_sha256':{str(x.name):e.digest(x) for x in [Path(__file__),e.HERE/'experiment.py',e.HERE/'build_harder.py']}})
    store=MemoryStore(out/'memories.json')
    runs=[]
    for task in data['tasks'][:a.limit]:
      path=out/f"{task['split']}_{task['id']}_none_0"/'run.json'
      runs.append(e.load(path) if path.exists() else e.run_task(task,'none',out,store,0))
      e.report(out,[r for r in runs if r['split']=='evaluation'],[r for r in runs if r['split']=='practice'],{})
    rows=[]
    for family in sorted({t['family'] for t in data['tasks']}):
      group=[r for r in runs if r['task_id'].split('_')[1]==family]
      rows.append({'family':family,'runs':len(group),'passed':sum(r['evaluation']['success'] for r in group),'tool_errors':sum(r['tool_errors'] for r in group)})
    e.save(out/'calibration.json',{'families':rows,'runs':len(runs),'passed':sum(r['evaluation']['success'] for r in runs),'note':'Baseline only. Synthetic families; no cross-session error-reduction claim.'})
    print(json.dumps({'output':str(out),'families':rows},indent=2),flush=True)
if __name__=='__main__':main()

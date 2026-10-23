"""Practice-only memory building, then matched fresh held-out comparisons."""
import argparse,json,random,uuid
from pathlib import Path
import experiment as e
from memory import MemoryStore
FORMAT = '\nOutput format requirements: Return only one JSON object. Each value must be a plain answer string containing only the requested number, without units or commentary. The file must be the actual path relative to corpus/; never copy a placeholder path. Evidence quotes must be exact source text. For computed fields, cite the calculation rule; also provide the separately requested input fields with their evidence.'
def main():
 p=argparse.ArgumentParser();p.add_argument('--repeats',type=int,default=1);p.add_argument('--resume',type=Path);p.add_argument('--practice-only',action='store_true');a=p.parse_args()
 if not 1<=a.repeats<=5:raise SystemExit('repeats must be 1..5')
 e.DATA=e.HERE/'dataset_v3';e.SYSTEM=e.SYSTEM.replace('supplied corpus/ notebooks','supplied corpus/ notebooks and configuration reference documents').replace('chapterXX/notebook.ipynb','actual_folder/actual_file.ipynb')+FORMAT
 # invoke has a bound default system argument; explicitly wrap it to use the clarified prompt.
 original=e.invoke
 def invoke(folder,prompt,system=None,review=False):return original(folder,prompt,e.SYSTEM if system is None or system==e.invoke_original_system else system,review)
 e.invoke_original_system=original.__defaults__[0]
 e.invoke=invoke
 data=e.load(e.DATA/'tasks.json');out=a.resume.resolve() if a.resume else e.HERE/'runs'/('multihop_'+uuid.uuid4().hex[:10]);out.mkdir(parents=True,exist_ok=True)
 manifest={'dataset_version':data['version'],'dataset_hash':e.digest(e.DATA/'tasks.json'),'corpus_hash':e.digest(e.DATA/'manifest.json'),'system_prompt':e.SYSTEM,'provider':'particle-ai','model':'glm-5.3-flash','pi_version':e.load(e.ROOT/'node_modules/@earendil-works/pi-coding-agent/package.json')['version'],'conditions':e.CONDITIONS,'repeats':a.repeats,'seed':73,'code_hashes':{str(x.name):e.digest(x) for x in [Path(__file__),e.HERE/'experiment.py',e.HERE/'memory.py',e.HERE/'build_multihop.py']}}
 if (out/'manifest.json').exists():
  old=e.load(out/'manifest.json')
  if old!=manifest:raise SystemExit('Resume configuration mismatch; use a new experiment.')
 else:e.save(out/'manifest.json',manifest)
 store=MemoryStore(out/'memories.json');practice=[]
 def run(task,condition,rep):
  path=out/f"{task['split']}_{task['id']}_{condition}_{rep}"/'run.json'
  return e.load(path) if path.exists() else e.run_task(task,condition,out,store,rep)
 for t in data['tasks']:
  if t['split']=='practice':practice.append(run(t,'none',0))
 if (out/'reviewer/run.json').exists():reviewed=e.load(out/'reviewer/run.json')
 else:reviewed=e.review(practice,out,store)
 e.save(out/'frozen_memories.json',store.records)
 if a.practice_only:
  print('Practice and review saved:',out,flush=True);return
 runs=[];rng=random.Random(73)
 for t in data['tasks']:
  if t['split']!='evaluation':continue
  for rep in range(a.repeats):
   conditions=e.CONDITIONS.copy();rng.shuffle(conditions)
   for condition in conditions:
    runs.append(run(t,condition,rep));e.report(out,runs,practice,reviewed)
 print('Completed:',out,flush=True)
if __name__=='__main__':main()

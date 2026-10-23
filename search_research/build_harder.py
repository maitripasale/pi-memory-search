"""Deterministic synthetic search benchmark; never executes fixture code."""
import hashlib,json,random
from pathlib import Path
HERE=Path(__file__).resolve().parent
DATA=HERE/'dataset_v2'

def write(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,indent=2),encoding='utf-8')

def build():
    tasks=[]; hashes={}
    families=['comments','override','alias','scope','stale','missing']
    for fidx,family in enumerate(families):
      for variant in range(3):
        split='practice' if variant==0 else 'evaluation'
        tid=f'{split}_{family}_{variant}'
        chapter=tid; base=DATA/'corpus'/chapter
        rng=random.Random(300+fidx*10+variant)
        label=['cedar','harbor','orchid'][variant]+str(fidx)
        active=str(23+fidx*7+variant*5); old=str(91+variant)
        cells=[]; facts={}
        def notebook(filename,sources):
            nb={'nbformat':4,'nbformat_minor':5,'metadata':{},'cells':[{'id':f'cell{i}','cell_type':'markdown' if src.startswith('# ') else 'code','metadata':{},'source':src.splitlines(True),**({} if src.startswith('# ') else {'execution_count':None,'outputs':[]})} for i,src in enumerate(sources)]}
            write(base/filename,nb)
            hashes[f'{chapter}/{filename}']=hashlib.sha256((base/filename).read_bytes()).hexdigest()
        def fact(name,value,file,cell,quote):
            facts[name]={'answer':value,'file':f'{chapter}/{file}','cell':cell,'quote':quote,'aliases':[]}
        # Different layouts and values; filenames never encode the answer.
        filenames=[f'notes_{n:02}.ipynb' for n in range(28)]
        rng.shuffle(filenames); a,b,c=filenames[:3]
        if family=='comments':
            question=f'For service {label}, find the active worker limit in its current example. Ignore comments and historical examples. Return field worker_limit.'
            notebook(a,[f'# Historical {label} worker example\nSuperseded; do not use as current configuration.',f'worker_limit = {old}'])
            notebook(b,[f'# Current {label} example',f'# worker_limit = {old}  # retired setting\nworker_limit = {active}'])
            fact('worker_limit',active,b,1,f'worker_limit = {active}')
        elif family=='override':
            question=f'What is the effective retry limit for service {label} in the staging profile? Follow the documented override chain. Return field retry_limit.'
            notebook(a,[f'# Profile catalogue\nService {label} staging starts from {b}; then apply {c}. Later explicitly defined keys replace earlier values.'])
            notebook(b,[f'# Base profile for {label}',f'retry_limit = {old}\nworker_limit = 4'])
            notebook(c,[f'# Staging overrides for {label}',f'retry_limit = {active}'])
            fact('retry_limit',active,c,1,f'retry_limit = {active}')
        elif family=='alias':
            question=f'Find the timeout used for the acknowledgement wait for service {label}. Return field acknowledgement_timeout.'
            notebook(a,[f'# Terminology for {label}\nThe acknowledgement wait is called the receipt window in this service. Its configuration key is receipt_window_ticks.'])
            notebook(b,[f'# Current {label} configuration',f'receipt_window_ticks = {active}'])
            fact('acknowledgement_timeout',active,b,1,f'receipt_window_ticks = {active}')
        elif family=='scope':
            question=f'Find the maximum batch size for the {label} service in the WEST deployment, not EAST or an example deployment. Return field batch_size.'
            notebook(a,[f'# {label} EAST current configuration',f'batch_size = {old}'])
            notebook(b,[f'# {label} WEST current configuration',f'batch_size = {active}'])
            notebook(c,[f'# {label} WEST retired example',f'batch_size = {old}'])
            fact('batch_size',active,b,1,f'batch_size = {active}')
        elif family=='stale':
            question=f'Find the current queue depth for {label} as selected by its release catalogue. File order and filename numbers do not indicate recency. Return field queue_depth.'
            notebook(a,[f'# Release catalogue for {label}\nThe deployment selects revision R{variant+4} in {b}. The other revision is retired.'])
            notebook(b,[f'# {label} revision R{variant+4}',f'queue_depth = {active}'])
            notebook(c,[f'# {label} revision R{variant+3} retired',f'queue_depth = {old}'])
            fact('queue_depth',active,b,1,f'queue_depth = {active}')
        else:
            question=f'Find an explicitly configured maximum retry count for service {label}. Do not confuse delay or timeout with count, and do not assume defaults. Return field maximum_retry_count; use unknown if no explicit count is present.'
            notebook(a,[f'# Current {label} configuration\nNo retry-count setting is documented in these supplied sources.',f'retry_delay_ticks = {active}\nretry_timeout_ticks = {old}'])
            facts['maximum_retry_count']={'answer':'unknown','aliases':[],'absent':True,'forbidden_pattern':'maximum_retry_count ='}
        for file in filenames:
            if (base/file).exists(): continue
            other=rng.choice(['pine','spruce','maple','birch'])+str(rng.randrange(1000))
            notebook(file,[f'# {other} service configuration\nUnrelated service; retain its own deployment scope.',f'worker_limit = {rng.randrange(3,100)}\nretry_limit = {rng.randrange(3,100)}\nreceipt_window_ticks = {rng.randrange(3,100)}\nbatch_size = {rng.randrange(3,100)}\nqueue_depth = {rng.randrange(3,100)}', '# Notes\nAcknowledgement wait, retry policy, staging, EAST and WEST are service-specific. Do not transfer values between services.'])
        tasks.append({'id':tid,'split':split,'family':family,'chapters':[chapter],'question':question,'facts':facts})
    # Independently read every anchor back from disk and prove absent keys absent.
    for task in tasks:
      for g in task['facts'].values():
        if g.get('absent'):
          assert not any(g['forbidden_pattern'] in ''.join(c['source']) for p in (DATA/'corpus'/task['id']).glob('*.ipynb') for c in json.loads(p.read_text())['cells'])
        else:
          source=''.join(json.loads((DATA/'corpus'/g['file']).read_text())['cells'][g['cell']]['source'])
          assert g['quote'] in source and str(g['answer']) in g['quote']
    write(DATA/'tasks.json',{'version':'2.0.0','source':'hand-authored synthetic fixtures','tasks':tasks,'limitations':['Shared task families test near transfer, not broad generalization.','No-memory calibration must establish actual difficulty.','Unknown scoring checks abstention but does not validate exhaustive search.']})
    write(DATA/'manifest.json',{'version':'2.0.0','seed_policy':'300 + family_index*10 + variant','sha256':hashes})
    print(f'Verified {len(tasks)} tasks: 6 practice, 12 evaluation; {len(hashes)} notebooks.')
if __name__=='__main__': build()

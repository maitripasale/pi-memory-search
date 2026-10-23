"""Versioned multi-file search benchmark with independently checked gold."""
import json,random,hashlib
from pathlib import Path
DATA=Path(__file__).resolve().parent/'dataset_v3'
def save(p,obj):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,indent=2),encoding='utf-8')
def build():
 tasks=[]
 for family in ['routing','aliases','precedence']:
  for variant in range(3):
   split='practice' if variant==0 else 'evaluation';tid=f'{split}_{family}_{variant}'
   rng=random.Random(712+['routing','aliases','precedence'].index(family)*50+variant)
   names=[f'artifact_{i:03}.ipynb' for i in range(96)];rng.shuffle(names)
   base=DATA/'corpus'/tid;service=['larch','azalea','willow'][variant]+'_'+family
   scope=['north','west','south'][variant];rev=f'r{variant+7}'
   val=31+variant*13+['routing','aliases','precedence'].index(family)*17;delta=3+variant
   docs={};facts={}
   def nb(name,sources):
    docs[name]=sources
    save(base/name,{'nbformat':4,'nbformat_minor':5,'metadata':{},'cells':[{'id':f'c{i}','cell_type':'markdown','metadata':{},'source':s.splitlines(True)} for i,s in enumerate(sources)]})
   def fact(k,answer,file,cell,quote): facts[k]={'answer':str(answer),'file':f'{tid}/{file}','cell':cell,'quote':quote,'aliases':[]}
   a,b,c,d,e,f,g=names[:7]
   if family=='routing':
    nb(a,[f'# Deployment catalogue\nService {service}, region {scope}, environment staging resolves release_handle = release_{rev}.',f'Same service in production uses release_handle = release_old.'])
    nb(b,[f'# Release handles\nrelease_{rev} resolves bundle_ref = bundle_{rev}_live.\nrelease_old resolves bundle_ref = bundle_retired.'])
    nb(c,[f'# Bundle manifest\nbundle_{rev}_live: use policy_ref = policy_{service}_selected.'])
    nb(d,[f'# Policy binding\npolicy_{service}_selected: base_ref = {e}; overlay_ref = {f}; calculation_ref = {g}.'])
    nb(e,[f'# Base settings selected by policy\nbase_limit = {val}'])
    nb(f,[f'# Overlay selected by policy\nlimit_adjustment = {delta}'])
    nb(g,['# Calculation rule\neffective_limit = base_limit + limit_adjustment'])
    q=f'For service {service} in {scope} staging, resolve its selected release and policy. Return fields base_limit, limit_adjustment, effective_limit for the final configuration.'
    fact('base_limit',val,e,0,f'base_limit = {val}');fact('limit_adjustment',delta,f,0,f'limit_adjustment = {delta}');fact('effective_limit',val+delta,g,0,'effective_limit = base_limit + limit_adjustment')
   elif family=='aliases':
    nb(a,[f'# Service vocabulary\nFor {service}, an acknowledgement wait is called a receipt window. The term response deadline belongs to a different feature.'])
    nb(b,[f'# Region-specific key map\nFor service {service} in {scope}, receipt window maps to profile_id = receipt_{rev}. Other regions use receipt_retired.'])
    nb(c,[f'# Receipt profile selector\nreceipt_{rev}: settings_ref = {d}; units_ref = {e}.'])
    nb(d,[f'# Receipt profile settings\nwindow_magnitude = {val}'])
    nb(e,[f'# Unit map for receipt_{rev}\nEach tick is {delta} milliseconds.'])
    nb(f,['# Conversion rule\nwait_ms = window_magnitude * milliseconds_per_tick'])
    nb(g,[f'# Deprecated feature\nFor {service}, response deadline = 999 milliseconds; this is not the receipt window.'])
    q=f'Find the acknowledgement wait for service {service} in {scope}. Return fields window_magnitude, milliseconds_per_tick, wait_ms. Use the region-selected profile and documented units.'
    fact('window_magnitude',val,d,0,f'window_magnitude = {val}');fact('milliseconds_per_tick',delta,e,0,f'Each tick is {delta} milliseconds.');fact('wait_ms',val*delta,f,0,'wait_ms = window_magnitude * milliseconds_per_tick')
   else:
    nb(a,[f'# Active deployment catalogue\nService {service} in {scope} selects revision {rev}. It loads {b} then {c} then {d}, using rules in {e}.'])
    nb(b,[f'# Revision {rev} base\nqueue_limit = {val}'])
    nb(c,[f'# Revision {rev} region overlay\nregion = {scope}\nqueue_limit = {val+delta}'])
    nb(d,[f'# Emergency overlay\nenabled = false\nqueue_limit = 997'])
    nb(e,['# Merge rules\nLater enabled matching-region values replace earlier ones. Disabled overlays do not apply. A revision not selected by the deployment catalogue does not apply.'])
    nb(f,[f'# Retired deployment revision r99\nService {service} in {scope}\nqueue_limit = 998'])
    nb(g,[f'# Historical note\nService {service} previously used queue_limit = 999.'])
    q=f'Find the effective queue limit for service {service} in {scope}, according to its selected revision and merge rules. Return fields base_limit, region_limit, effective_limit. Do not select disabled overlays or retired revisions.'
    fact('base_limit',val,b,0,f'queue_limit = {val}');fact('region_limit',val+delta,c,0,f'queue_limit = {val+delta}');fact('effective_limit',val+delta,c,0,f'queue_limit = {val+delta}')
   for i,name in enumerate(names[7:]):
    other=f'{service}_other_{i}'
    nb(name,[f'# Service catalogue for {other}\nEnvironment staging; region {scope}; release_handle = noise_{i}.',f'# Historical settings\nbase_limit = {rng.randrange(5,300)}\nlimit_adjustment = {rng.randrange(1,15)}\nqueue_limit = {rng.randrange(5,300)}',f'# Terminology\nAcknowledgement wait, receipt window, response deadline and unit map are scoped to {other}.',f'# Revision routing\nnoise_{i} selects other_bundle_{i}. These settings do not apply to another service.'])
   for k,gold in facts.items(): assert gold['quote'] in docs[gold['file'].split('/')[-1]][gold['cell']]
   tasks.append({'id':tid,'split':split,'family':family,'chapters':[tid],'question':q,'facts':facts})
 files={str(p.relative_to(DATA/'corpus')).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in (DATA/'corpus').glob('*/*.ipynb')}
 save(DATA/'tasks.json',{'version':'3.0.0','source':'synthetic multi-file configuration fixtures','tasks':tasks,'limitations':['Near transfer across shared task families; not broad generalization.','Strict citations check selected anchors; do not validate every intermediate reasoning step.']})
 save(DATA/'manifest.json',{'version':'3.0.0','files':files})
 print(f'Validated {len(tasks)} tasks, 27 gold anchors, {len(files)} notebooks.')
if __name__=='__main__':build()

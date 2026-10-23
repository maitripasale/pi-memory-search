"""Small versioned memory store. Only practice evidence may produce memories."""
import ast
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path


def now(): return datetime.now(timezone.utc).isoformat()
def terms(text): return set(re.findall(r'[a-z]{3,}', text.lower()))


def empty_conditional_scan(run, call_id, result):
    # Recognize a narrowly defined scan: conditional printing in a loop,
    # followed by print('done'), whose only stdout was 'done'.
    call=next((c for c in run.get('calls',[]) if c.get('id')==call_id and c.get('name')=='python_cell'),None)
    if not call: return False
    text='\n'.join(c.get('text','') for c in result.get('content',[]) if c.get('type')=='text')
    stdout=text.split('\nNotebook:',1)[0].strip()
    if stdout!='done': return False
    try: tree=ast.parse(call.get('arguments',{}).get('code',''))
    except SyntaxError:return False
    if len(tree.body)!=2 or not isinstance(tree.body[0],ast.For):return False
    loop=tree.body[0]
    if not any(isinstance(node,ast.If) and any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='print' for n in ast.walk(node)) for node in loop.body):return False
    end=tree.body[1]
    return (isinstance(end,ast.Expr) and isinstance(end.value,ast.Call)
            and isinstance(end.value.func,ast.Name) and end.value.func.id=='print'
            and len(end.value.args)==1 and isinstance(end.value.args[0],ast.Constant) and end.value.args[0].value=='done')


class MemoryStore:
    def __init__(self, path, max_bytes=32000):
        self.path=Path(path)
        self.max_bytes=max_bytes
        self.records=json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else []

    def save(self):
        data=json.dumps(self.records,indent=2,ensure_ascii=False)
        if len(data.encode('utf-8'))>self.max_bytes: raise ValueError('Memory storage budget exceeded')
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.path.write_text(data,encoding='utf-8')

    def write(self, candidate, practice_runs):
        kind=candidate.get('type')
        if kind not in ('procedural','metacognitive'): raise ValueError('Unknown memory type')
        lesson=candidate.get('lesson','').strip()
        if not lesson or len(lesson)>1200: raise ValueError('Invalid lesson length')
        evidence=candidate.get('evidence',[])
        if not evidence: raise ValueError('Missing evidence')
        observed_problem=False
        for item in evidence:
            run=practice_runs.get(item.get('run_id'))
            if not run or run['split']!='practice': raise ValueError('Only practice runs may build memory')
            matches=[r for r in run['results'] if r.get('toolCallId')==item.get('tool_call_id')]
            if not matches: raise ValueError('Unknown evidence tool call')
            for result in matches:
                text=json.dumps(result.get('content',[]))
                observed_problem |= empty_conditional_scan(run,item.get('tool_call_id'),result) or bool(result.get('isError')) or bool(re.search(r'no (?:hits|matches|results)|not found|\[\]|0 (?:hits|matches|results)',text,re.I))
        if kind=='metacognitive' and not observed_problem:
            raise ValueError('Metacognitive candidate lacks an observed error or empty result')
        # Prevent promoting notebook-specific factual answers as general skills.
        if re.search(r'chapter\d|\.ipynb|all-mpnet|DenoisingAutoEncoderLoss',lesson,re.I):
            raise ValueError('Lesson contains corpus-specific facts rather than a reusable method')
        record={'id':uuid.uuid4().hex[:12],'type':kind,'lesson':lesson,
                'trigger':candidate.get('trigger','notebook search'), 'tags':candidate.get('tags',[]),
                'scope':'notebook-source-search','evidence':evidence,'created_at':now(),'updated_at':now(),
                'version':1,'active':True,'expires_at':None,'conflict_key':candidate.get('conflict_key'),
                'status':'evidence-linked candidate; semantic usefulness unverified'}
        self.records.append(record)
        try: self.save()
        except Exception:
            self.records.pop(); raise
        return record

    def revise(self, id, lesson):
        # New revisions require revalidation by the caller before evaluation use.
        r=next(x for x in self.records if x['id']==id)
        old=json.loads(json.dumps(r))
        r.setdefault('revisions',[]).append({'version':r['version'],'lesson':r['lesson'],'updated_at':r['updated_at']})
        r.update(lesson=lesson,version=r['version']+1,updated_at=now(),status='needs_review')
        try: self.save()
        except Exception:
            r.clear(); r.update(old); raise

    def forget(self,id):
        r=next(x for x in self.records if x['id']==id)
        r.update(active=False,updated_at=now()); self.save()

    def retrieve(self, question, condition, byte_budget=3000):
        kinds={'none':[], 'procedural':['procedural'],'metacognitive':['metacognitive'],
               'both':['procedural','metacognitive']}[condition]
        q=terms(question+' notebook source search python code cells')
        pool=[r for r in self.records if r['active'] and r['type'] in kinds
              and r['scope']=='notebook-source-search' and r['status']!='needs_review'
              and (not r['expires_at'] or r['expires_at']>now())]
        # Explicitly marked conflicting lessons are withheld, rather than choosing arbitrarily.
        counts={}
        for r in pool:
            if r.get('conflict_key'): counts[r['conflict_key']]=counts.get(r['conflict_key'],0)+1
        pool=[r for r in pool if not r.get('conflict_key') or counts[r['conflict_key']]==1]
        pool.sort(key=lambda r:(-len(q & terms(r['trigger']+' '+r['lesson']+' '+' '.join(r['tags']))),r['id']))
        selected=[]; parts=[]; used=0
        per_type=byte_budget//max(1,len(kinds)); spent={k:0 for k in kinds}
        for r in pool:
            if not (q & terms(r['trigger']+' '+r['lesson'])): continue
            text=f"[{r['type']} / {r['id']}] When: {r['trigger']}\nLesson: {r['lesson']}\n"
            size=len(text.encode('utf-8'))
            if used+size<=byte_budget and spent[r['type']]+size<=per_type:
                selected.append(r['id']); parts.append(text); used+=size; spent[r['type']]+=size
        return {'ids':selected,'text':'\n'.join(parts),'bytes':used,'budget_bytes':byte_budget}

"""Local, read-only viewer for saved experiments. No model calls."""
import argparse, json
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
ROOT = Path(__file__).resolve().parent

def load_data():
    experiments=[]
    for folder in sorted((ROOT/'runs').glob('*'), key=lambda p:p.stat().st_mtime, reverse=True):
        report=folder/'audited_report.json' if (folder/'audited_report.json').exists() else folder/'report.json'
        if not report.exists(): continue
        summary=json.loads(report.read_text(encoding='utf-8')).get('summary',{})
        if not summary: continue
        runs=[]
        for file in sorted(folder.glob('*/run.json')):
            r=json.loads(file.read_text(encoding='utf-8'))
            if (file.parent/'evaluation.audited.json').exists(): r['evaluation']=json.loads((file.parent/'evaluation.audited.json').read_text(encoding='utf-8'))
            if not r.get('condition'): continue
            runs.append({k:r.get(k) for k in ['task_id','condition','evaluation','retrieval','calls','results','response','tokens','seconds']})
        memory=folder/'memories.json'
        experiments.append({'id':folder.name,'summary':summary,'audit':json.loads((folder/'audit.json').read_text(encoding='utf-8')) if (folder/'audit.json').exists() else None,'memories':json.loads(memory.read_text(encoding='utf-8')) if memory.exists() else [],'runs':runs})
    return experiments

HTML = r"""<!doctype html><html><meta charset="utf-8"><title>Pi memory research</title>
<style>body{font:16px system-ui;background:#101725;color:#e5edf7;margin:0;padding:32px;max-width:1300px;margin:auto}h1{margin-bottom:8px}p{color:#aabbd1}select,button{padding:10px;background:#23334c;color:white;border:1px solid #455b79;border-radius:8px}section{background:#19253a;padding:22px;border-radius:12px;margin:20px 0}table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:12px;border-bottom:1px solid #34445d}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#0d1523;padding:16px;border-radius:8px;font-size:13px}summary{cursor:pointer;padding:12px}article{border-left:3px solid #70b9ff;padding-left:16px;margin:18px 0}.bar{height:8px;background:#6ab7ff;border-radius:4px;margin-top:8px}.tag{color:#80d9b2}label{margin-right:12px}</style>
<h1>Pi memory research</h1><p>Saved runs Â· Agent-written Python Â· Evidence-backed memory candidates</p>
<label>Experiment <select id="experiment"></select></label><button id="refresh">Refresh saved files</button>
<section><b>Practice â†’ run review â†’ stored lessons â†’ fresh sessions â†’ comparison</b><p>This viewer does not start experiments. Injection shows what the agent received; it does not prove reuse. The pilot has not demonstrated improvement.</p></section>
<section><h2>Comparison</h2><div id="comparison"></div></section>
<section><h2>Result notes</h2><div id="audit"></div></section><section><h2>Memory candidates</h2><div id="memory"></div></section>
<section><h2>Inspect an agent run</h2><select id="run"></select><div id="detail"></div></section>
<script>
let data=[];const el=id=>document.getElementById(id);const escape=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));const pretty=v=>escape(JSON.stringify(v,null,2));
function render(){const x=data[Number(el('experiment').value)];if(!x)return;
el('comparison').innerHTML='<table><tr><th>Condition</th><th>Passed</th><th>Tool calls</th><th>Errors</th><th>Tokens</th><th>Seconds</th></tr>'+Object.entries(x.summary).map(([k,v])=>`<tr><td>${escape(k)}<div class="bar" style="width:${100*v.success_fraction}%"></div></td><td>${v.passed}/${v.runs}</td><td>${v.mean_tool_calls}</td><td>${v.tool_errors}</td><td>${v.mean_tokens}</td><td>${v.mean_seconds}</td></tr>`).join('')+'</table>';
el('audit').textContent=x.audit?.summary || 'Small pilot; no memory benefit demonstrated.';
el('memory').innerHTML=x.memories.map(m=>`<article><b class="tag">${escape(m.type)}</b><p>${escape(m.lesson)}</p><details><summary>Provenance and lifecycle</summary><pre>${pretty(m)}</pre></details></article>`).join('') || '<p>No memory records for this experiment.</p>';
el('run').innerHTML=x.runs.map((r,i)=>`<option value="${i}">${escape(r.task_id)} / ${escape(r.condition)}</option>`).join('');renderRun();}
function renderRun(){const r=data[Number(el('experiment').value)]?.runs[Number(el('run').value)];if(!r)return;el('detail').innerHTML=`<p>Evaluation: <b>${r.evaluation?.success?'Passed':'Failed'}</b> Â· Tool calls: ${(r.calls||[]).length}</p><details open><summary>Injected memory</summary><pre>${pretty(r.retrieval)}</pre></details>`+(r.calls||[]).map((c,i)=>{const result=(r.results||[]).find(t=>t.toolCallId===c.id);return `<details ${i===0?'open':''}><summary>Step ${i+1}: ${escape(c.name)}</summary><pre>${escape(c.arguments?.code||JSON.stringify(c.arguments,null,2))}</pre><b>Observed result</b><pre>${escape((result?.content||[]).filter(t=>t.type==='text').map(t=>t.text).join('\n'))}</pre></details>`}).join('')+`<details><summary>Answer and evaluation</summary><pre>${pretty(r.response)}</pre><pre>${pretty(r.evaluation)}</pre></details>`;}
async function refresh(){data=await(await fetch('/api/experiments')).json();el('experiment').innerHTML=data.map((x,i)=>`<option value="${i}">${escape(x.id)}</option>`).join('');render();}
el('experiment').onchange=render;el('run').onchange=renderRun;el('refresh').onclick=refresh;refresh();
</script></html>"""
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path=='/': body=HTML.encode();kind='text/html; charset=utf-8'
        elif self.path=='/api/experiments': body=json.dumps(load_data()).encode();kind='application/json'
        else: self.send_error(404);return
        self.send_response(200);self.send_header('Content-Type',kind);self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    def log_message(self,*args): pass
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8765);a=p.parse_args()
    print(f'Dashboard: http://127.0.0.1:{a.port}',flush=True)
    ThreadingHTTPServer(('127.0.0.1',a.port),Handler).serve_forever()

import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from memory import MemoryStore, empty_conditional_scan
from experiment import evaluate,load,DATA

class ResearchTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.store=MemoryStore(Path(self.tmp.name)/'memories.json')
        self.runs={'practice':{'split':'practice','results':[{'toolCallId':'c','isError':True,'content':[{'text':'UnicodeDecodeError: bad input'}]}]}}
        self.candidate={'type':'metacognitive','trigger':'notebook search','lesson':'When notebook reads fail, check the text encoding before searching again.','evidence':[{'run_id':'practice','tool_call_id':'c'}]}
    def test_empty_scan_evidence(self):
        run={'calls':[{'id':'c','name':'python_cell','arguments':{'code':"for c in cells:\n    if 'needle' in c:\n        print(c)\nprint('done')"}}]}
        result={'content':[{'type':'text','text':'done\n\nNotebook: test.ipynb'}]}
        self.assertTrue(empty_conditional_scan(run,'c',result))
        result['content'][0]['text']='needle\ndone'
        self.assertFalse(empty_conditional_scan(run,'c',result))
        run['calls'][0]['arguments']['code']="print('done')"
        result['content'][0]['text']='done'
        self.assertFalse(empty_conditional_scan(run,'c',result))

    def test_gold_evidence(self):
        for t in load(DATA/'tasks.json')['tasks']:
            if any(v.get('absent') for v in t['facts'].values()):
                self.assertTrue(evaluate(t,json.dumps({'answers':{'class_weight':{'value':'unknown'}}}),DATA/'corpus')['success'])
                self.assertFalse(evaluate(t,json.dumps({'answers':{'class_weight':{'value':'balanced'}}}),DATA/'corpus')['success'])
                continue
            answers={k:{'value':v['answer'],'file':v['file'],'cell':v['cell'],'quote':v['quote']} for k,v in t['facts'].items()}
            self.assertTrue(evaluate(t,json.dumps({'answers':answers}),DATA/'corpus')['success'])
            for a in answers.values():a['quote']='fabricated evidence'
            self.assertFalse(evaluate(t,json.dumps({'answers':answers}),DATA/'corpus')['success'])
    def test_practice_only(self):
        self.runs['practice']['split']='evaluation'
        with self.assertRaises(ValueError):self.store.write(self.candidate,self.runs)
    def test_unknown_evidence(self):
        self.candidate['evidence'][0]['tool_call_id']='invented'
        with self.assertRaises(ValueError):self.store.write(self.candidate,self.runs)
    def test_no_invented_weakness(self):
        self.runs['practice']['results'][0].update(isError=False,content=[{'text':'Found matches'}])
        with self.assertRaises(ValueError):self.store.write(self.candidate,self.runs)
    def test_conditions_and_budget(self):
        r=self.store.write(self.candidate,self.runs)
        self.assertEqual(self.store.retrieve('search','none')['ids'],[])
        self.assertEqual(self.store.retrieve('search','procedural')['ids'],[])
        self.assertEqual(self.store.retrieve('search','metacognitive')['ids'],[r['id']])
        self.assertEqual(self.store.retrieve('search','metacognitive',0)['ids'],[])
    def test_expiry_conflict_forget_revise(self):
        r=self.store.write(self.candidate,self.runs)
        r['expires_at']='2000-01-01T00:00:00+00:00'
        self.assertEqual(self.store.retrieve('search','metacognitive')['ids'],[])
        r['expires_at']=None; r['conflict_key']='encoding'
        self.candidate['conflict_key']='encoding'; other=self.store.write(self.candidate,self.runs)
        self.assertEqual(self.store.retrieve('search','metacognitive')['ids'],[])
        self.store.forget(other['id'])
        self.assertEqual(self.store.retrieve('search','metacognitive')['ids'],[r['id']])
        self.store.revise(r['id'],'Revised search method')
        self.assertEqual(self.store.retrieve('search','metacognitive')['ids'],[])
    def test_storage_budget(self):
        self.store.max_bytes=1
        with self.assertRaises(ValueError):self.store.write(self.candidate,self.runs)
        self.assertEqual(self.store.records,[])

if __name__=='__main__':unittest.main()

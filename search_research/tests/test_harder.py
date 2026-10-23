import json,sys,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
import experiment as e

class HarderDatasetTests(unittest.TestCase):
    def test_split_and_evidence(self):
        data=e.load(HERE/'dataset_v2/tasks.json')
        tasks=data['tasks']
        self.assertEqual(sum(t['split']=='practice' for t in tasks),6)
        self.assertEqual(sum(t['split']=='evaluation' for t in tasks),12)
        self.assertEqual(len(set(t['id'] for t in tasks)),18)
        for t in tasks:
            answers={}
            for k,g in t['facts'].items():
                answers[k]={'value':g['answer']} if g.get('absent') else {'value':g['answer'],'file':g['file'],'cell':g['cell'],'quote':g['quote']}
            self.assertTrue(e.evaluate(t,json.dumps({'answers':answers}),HERE/'dataset_v2/corpus')['success'],t['id'])
    def test_wrong_answers_rejected(self):
        for t in e.load(HERE/'dataset_v2/tasks.json')['tasks']:
            answers={k:{'value':'999999','file':g.get('file',''),'cell':g.get('cell',0),'quote':g.get('quote','')} for k,g in t['facts'].items()}
            self.assertFalse(e.evaluate(t,json.dumps({'answers':answers}),HERE/'dataset_v2/corpus')['success'])
    def test_correct_value_wrong_scope_rejected(self):
        t=e.load(HERE/'dataset_v2/tasks.json')['tasks'][0]
        k,g=next(iter(t['facts'].items()))
        wrong={'value':g['answer'],'file':g['file'],'cell':0,'quote':'# fabricated evidence'}
        self.assertFalse(e.evaluate(t,json.dumps({'answers':{k:wrong}}),HERE/'dataset_v2/corpus')['success'])
if __name__=='__main__':unittest.main()

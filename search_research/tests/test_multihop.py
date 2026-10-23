import unittest,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
import experiment as e
from audit_multihop import audited_evaluation
class MultiHopTests(unittest.TestCase):
 def test_answers_and_corrupt_evidence(self):
  tasks=e.load(HERE/'dataset_v3/tasks.json')['tasks']
  self.assertEqual(len(tasks),9)
  self.assertEqual(sum(t['split']=='practice' for t in tasks),3)
  for t in tasks:
   answers={k:{'value':g['answer'],'file':g['file'],'cell':g['cell'],'quote':g['quote']} for k,g in t['facts'].items()}
   self.assertTrue(e.evaluate(t,json.dumps({'answers':answers}),HERE/'dataset_v3/corpus')['success'])
   for answer in answers.values():answer['quote']='fabricated supporting text'
   self.assertFalse(e.evaluate(t,json.dumps({'answers':answers}),HERE/'dataset_v3/corpus')['success'])
 def test_merge_rule_evidence(self):
  for t in e.load(HERE/'dataset_v3/tasks.json')['tasks']:
   if t['family']!='precedence':continue
   answers={k:{'value':g['answer'],'file':g['file'],'cell':g['cell'],'quote':g['quote']} for k,g in t['facts'].items()}
   for p in (HERE/'dataset_v3/corpus'/t['id']).glob('*.ipynb'):
    text=''.join(e.load(p)['cells'][0]['source'])
    if text.startswith('# Merge rules'):
     answers['effective_limit'].update(file=p.relative_to(HERE/'dataset_v3/corpus').as_posix(),cell=0,quote=text)
   self.assertTrue(audited_evaluation(t,json.dumps({'answers':answers}),HERE/'dataset_v3/corpus')['success'])
   answers['effective_limit']['quote']='fabricated merge rule'
   self.assertFalse(audited_evaluation(t,json.dumps({'answers':answers}),HERE/'dataset_v3/corpus')['success'])
 def test_arithmetic(self):
  for t in e.load(HERE/'dataset_v3/tasks.json')['tasks']:
   f=t['facts']
   if t['family']=='routing':self.assertEqual(int(f['effective_limit']['answer']),int(f['base_limit']['answer'])+int(f['limit_adjustment']['answer']))
   elif t['family']=='aliases':self.assertEqual(int(f['wait_ms']['answer']),int(f['window_magnitude']['answer'])*int(f['milliseconds_per_tick']['answer']))
   else:self.assertEqual(f['effective_limit']['answer'],f['region_limit']['answer'])
if __name__=='__main__':unittest.main()

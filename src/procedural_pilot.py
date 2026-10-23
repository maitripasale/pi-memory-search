"""Small procedural-memory pilot. Rule-based extraction; not an automatic skill learner."""
import argparse
import hashlib
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from runner import run_baseline_task


def extract_lesson(run):
    if not run.get('evaluation', {}).get('success') or run.get('error'):
        raise ValueError('A successful practice run is required')
    results = {x['toolCallId']: x for x in run.get('observations', [])}
    steps, evidence = [], []
    for call in run.get('tool_calls', []):
        result = results.get(call['id'])
        if not result or result.get('isError'):
            continue
        name, args = call['name'], call.get('arguments', {})
        step = None
        if name == 'read':
            path = args.get('path', '')
            step = f'Read {path} if present and relevant; use the current contents.'
        elif name == 'write':
            step = 'Create the requested output or script using the current specification and task parameters.'
        elif name == 'bash':
            step = 'Run the implementation and check the produced output against the current project helper or specification.'
        if step and step not in steps:
            steps.append(step)
            evidence.append({'step': len(steps), 'tool_call_id': call['id'], 'tool': name})
    if not steps:
        raise ValueError('No supported successful actions to extract')
    return {'type': 'procedural', 'status': 'candidate', 'scope': 'shop_repo pricing tasks',
            'write_policy': 'deterministic action-to-step mapping v1',
            'source_run_id': run['run_id'], 'source_task_id': run['task_id'],
            'created_at': datetime.now(timezone.utc).isoformat(), 'steps': steps, 'evidence': evidence,
            'limitations': 'A single successful run supports this candidate; transfer benefit is unverified.'}


def prepare_tasks(out):
    # Entirely synthetic shopping-cart fixture; no authentication data.
    from decimal import Decimal, ROUND_HALF_UP
    files = {
        'shop_repo/README.md': 'Order totals: read config/pricing.md and src/pricing.py. Input is items.csv.\n',
        'shop_repo/config/pricing.md': 'Use decimal arithmetic. Sum quantity * unit_price. Apply 7.5% tax to the subtotal. Round the final total once to two decimals using ROUND_HALF_UP.\n',
        'shop_repo/src/pricing.py': "from decimal import Decimal, ROUND_HALF_UP\ndef total(rows):\n    subtotal = sum(Decimal(r['quantity']) * Decimal(r['unit_price']) for r in rows)\n    return (subtotal * Decimal('1.075')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)\n"
    }
    paths=[]
    for phase, csv_text in [('practice', 'quantity,unit_price\n3,1.25\n2,2.10\n'), ('evaluation', 'quantity,unit_price\n7,0.35\n3,1.99\n')]:
        import csv, io
        rows=list(csv.DictReader(io.StringIO(csv_text)))
        subtotal=sum(Decimal(r['quantity'])*Decimal(r['unit_price']) for r in rows)
        expected=str((subtotal*Decimal('1.075')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        task={'task_id': 'shopping_total_'+phase+'_v1', 'version':'1.0.0',
              'session_type': 'memory_building' if phase=='practice' else 'held_out_evaluation',
              'prompt':'Use shop_repo/ to calculate the total for items.csv under the project pricing rules. Save only the amount with two decimal places to shop_repo/total.txt. Verify your result.',
              'setup':{'files':dict(files, **{'shop_repo/items.csv':csv_text}), 'commands':[]},
              'evaluation':{'type':'file_content','target_file':'shop_repo/total.txt','expected_value':expected}}
        path=out/(phase+'.json')
        path.write_text(json.dumps(task,indent=2),encoding='utf-8')
        paths.append(path)
    return paths


def run_pilot():
    out = ROOT / 'results' / ('procedural_pilot_' + uuid.uuid4().hex[:10])
    out.mkdir(parents=True)
    practice, evaluation = prepare_tasks(out)
    config = ROOT / 'configs/baseline_frozen.json'
    snapshot = json.loads(config.read_text())
    snapshot['experiment_id'] = 'procedural_pilot_v1'
    snapshot['memory']['context_injection_budget_tokens'] = 1000
    snapshot['notes'] = ['Temperature and max_turns in original config are not enforced by the current CLI runner.',
                         'Filesystem isolation is a separate working directory, not a security sandbox.',
                         'Cost is unavailable; runner default 0.0 is not evidence of free usage.']
    config = out / 'config.json'
    config.write_text(json.dumps(snapshot, indent=2), encoding='utf-8')
    def execute(task, condition, context=None):
        prompt = json.loads(task.read_text())['prompt']
        config_data = json.loads(config.read_text())
        config_data['memory'].update({'type': 'procedural' if context else 'none', 'enabled': bool(context)})
        run_config = out / (condition + '_config.json')
        run_config.write_text(json.dumps(config_data, indent=2), encoding='utf-8')
        print('Running ' + condition, flush=True)
        result = run_baseline_task(str(task), str(run_config),
            prompt_override=(context + '\n\nTask:\n' + prompt) if context else None,
            injected_memory={'type': 'procedural', 'context': context, 'snapshot': str(out / 'lesson.json')} if context else None)
        log = json.loads(Path(result['saved_paths']['json_path']).read_text())
        return {'condition': condition, 'success': result['success'], 'duration_ms': result['duration_ms'],
                'tokens': result['token_usage']['total_tokens'], 'tool_calls': len(log['tool_calls']),
                'tool_errors': sum(bool(x.get('isError')) for x in log['observations']),
                'trajectory': result['saved_paths']['json_path'], 'error': result['error']}, log
    building, log = execute(practice, 'practice')
    lesson = extract_lesson(log)
    (out / 'lesson.json').write_text(json.dumps(lesson, indent=2), encoding='utf-8')
    context = 'Candidate procedure from a prior successful practice run. Check applicability to this task.\n' + '\n'.join(f'{i+1}. {s}' for i,s in enumerate(lesson['steps']))
    # UTF-8 bytes provide a conservative bound for byte-level tokenizers.
    if len(context.encode('utf-8')) > 1000:
        raise ValueError('Lesson exceeds conservative context budget')
    (out / 'lesson.txt').write_text(context, encoding='utf-8')
    rows = []
    # Reverse order on the second pair to reduce simple ordering effects.
    for condition in ['no_memory_1', 'procedural_1', 'procedural_2', 'no_memory_2']:
        row, _ = execute(evaluation, condition, context if condition.startswith('procedural') else None)
        rows.append(row)
        (out / 'results.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
    report = {'practice': building, 'runs': rows, 'lesson': str(out / 'lesson.json'),
              'conclusion': 'Pilot only: two runs per condition on one task. No general accuracy or repeated-error reduction claim.',
              'cost_usd': None, 'config': str(config)}
    (out / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2), flush=True)


def self_test():
    sample = {'run_id': 'practice', 'task_id': 'p', 'evaluation': {'success': True},
              'tool_calls': [{'id': 'a', 'name': 'read', 'arguments': {'path': 'repo/README.md'}},
                             {'id': 'b', 'name': 'read', 'arguments': {'path': 'failed.txt'}}],
              'observations': [{'toolCallId': 'a', 'isError': False}, {'toolCallId': 'b', 'isError': True}],
              'hidden_evaluation_data': {'answer': 'NEVER_COPY_THIS'}}
    lesson = extract_lesson(sample)
    assert len(lesson['steps']) == 1 and lesson['evidence'][0]['tool_call_id'] == 'a'
    assert 'NEVER_COPY_THIS' not in json.dumps(lesson)
    sample['evaluation']['success'] = False
    try:
        extract_lesson(sample)
    except ValueError:
        pass
    else:
        raise AssertionError('Failed practice accepted')
    print('PASS: evidence mapping, failed-action exclusion, answer exclusion, failed-run rejection')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    self_test() if args.self_test else run_pilot()

"""Live, bounded, risk-aware REPAIR-X recovery on controlled benchmark cases.

WARNING: subprocess validation is not a secure sandbox for untrusted code.
Run only with trusted fixtures in an isolated development environment.
"""
import argparse
import ast
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from benchmark.cases import CASES
from benchmark_runner import (build_prompt, check_tests, formatting_retry_prompt)
from auto_repair import clean_patch_text, replace_function_body
from llm_providers.factory import create_provider
from llm_providers.generate import generate_text
from risk_controller import MAX_ATTEMPTS, assess_patch

ROOT = Path(__file__).resolve().parent
HISTORY = ROOT / 'live_recovery_results.jsonl'


def make_retry_prompt(case, previous_body, reason):
    """Use failure feedback without revealing visible/hidden assertions."""
    return (build_prompt(case) + '\nYour previous attempt was rejected.\n'
            + 'Previous candidate body:\n' + previous_body[:3000]
            + '\nFailure category: ' + reason[:400]
            + '\nGenerate a revised function body. Do not repeat the same patch.')


def run_case(client, model, provider, case, max_attempts=MAX_ATTEMPTS, generator=generate_text,
             validator=check_tests):
    if not 1 <= max_attempts <= MAX_ATTEMPTS:
        raise ValueError('max_attempts must be between 1 and 3')
    original = case['source']
    started = time.perf_counter()
    record = {
        'run_id': uuid4().hex, 'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'provider': provider, 'model': model, 'case_id': case['id'],
        'workflow': 'live_ai_risk_recovery_v1', 'max_attempts': max_attempts,
        'attempts': [], 'outcome': 'ABSTAINED', 'original_unchanged': True,
        'rollback_semantics': 'discard temporary candidates; never write original fixture',
    }
    prompt = build_prompt(case)
    for attempt_no in range(1, max_attempts + 1):
        entry = {'attempt': attempt_no, 'patch': None, 'formatting_retries': 0,
                 'visible_pass': False, 'hidden_pass': False, 'risk': None,
                 'decision': 'REJECT', 'error': None}
        try:
            body = clean_patch_text(generator(client, model, prompt))
            entry['patch'] = body
            try:
                candidate = replace_function_body(original, case['function'], body)
            except (SyntaxError, IndentationError) as syntax_exc:
                entry['formatting_retries'] = 1
                body = clean_patch_text(generator(client, model, formatting_retry_prompt(case, body, syntax_exc)))
                entry['patch'] = body
                candidate = replace_function_body(original, case['function'], body)
            # Pre-execution heuristic only. It does not make generated code safe.
            pre = assess_patch(original, candidate, visible_pass=True, hidden_pass=True)
            if pre.action == 'REJECT':
                entry['risk'] = pre.to_dict()
                entry['error'] = 'blocked_by_pre_execution_risk'
            else:
                visible, visible_err = validator(candidate, case['function'], case['visible'])
                hidden, hidden_err = validator(candidate, case['function'], case['hidden'])
                entry['visible_pass'] = visible
                entry['hidden_pass'] = hidden
                decision = assess_patch(original, candidate, visible_pass=visible, hidden_pass=hidden)
                entry['risk'] = decision.to_dict()
                if decision.action == 'ACCEPT':
                    entry['decision'] = 'ACCEPT'
                    record['outcome'] = 'ACCEPTED'
                else:
                    entry['error'] = ('visible_validation_failed' if not visible else 'hidden_validation_failed')
        except Exception as exc:
            entry['error'] = f'{type(exc).__name__}: {str(exc)[:300]}'
        record['attempts'].append(entry)
        if entry['decision'] == 'ACCEPT':
            break
        # Feedback is intentionally categorical; no withheld tests are sent to the model.
        prompt = make_retry_prompt(case, entry['patch'] or '', entry['error'] or 'rejected_by_policy')
    record['elapsed_seconds'] = round(time.perf_counter() - started, 3)
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--provider', choices=['groq', 'gemini', 'openai'], default='groq')
    parser.add_argument('--case', choices=[case['id'] for case in CASES], default='divide_zero')
    parser.add_argument('--max-attempts', type=int, default=MAX_ATTEMPTS)
    parser.add_argument('--output', default=str(HISTORY))
    args = parser.parse_args()
    if not 1 <= args.max_attempts <= MAX_ATTEMPTS:
        parser.error('--max-attempts must be 1, 2, or 3')
    case = next(c for c in CASES if c['id'] == args.case)
    for group in ('visible', 'hidden'):
        ast.parse('from target import ' + case['function'] + '\n' + '\n'.join(case[group]) + '\n')
    client, model = create_provider(args.provider)
    report = run_case(client, model, args.provider, case, args.max_attempts)
    output = Path(args.output)
    with output.open('a', encoding='utf-8') as f:
        f.write(json.dumps(report, ensure_ascii=False) + '\n')
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print('Saved:', output)


if __name__ == '__main__':
    main()
